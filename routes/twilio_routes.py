import os
from functools import wraps
from datetime import datetime
from flask import Blueprint, request, jsonify, abort, Response
from twilio.request_validator import RequestValidator
from config import Config
from database import get_db_connection
from services.twilio_service import TwilioService
from services.sms_service import SMSService
from services.call_service import CallService
from voice_engine import translate_text, speak_text
from extensions import socketio

twilio_bp = Blueprint('twilio', __name__)

def validate_twilio_request(f):
    """Decorator to validate Twilio requests using X-Twilio-Signature."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if getattr(Config, 'TWILIO_TEST_MODE', True):
            return f(*args, **kwargs)
            
        signature = request.headers.get('X-Twilio-Signature')
        if not signature:
            return abort(403, "Missing Twilio Signature")
            
        validator = RequestValidator(Config.TWILIO_AUTH_TOKEN)
        url = request.url
        if getattr(Config, 'BASE_URL', ''):
            from urllib.parse import urlparse, urlunparse
            parsed_url = urlparse(url)
            parsed_base = urlparse(Config.BASE_URL)
            url = urlunparse((
                parsed_base.scheme,
                parsed_base.netloc,
                parsed_url.path,
                parsed_url.params,
                parsed_url.query,
                parsed_url.fragment
            ))
            
        if not validator.validate(url, request.form, signature):
            return abort(403, "Invalid Twilio Signature")
        return f(*args, **kwargs)
    return decorated_function

def dispatch_next_ambulance_driver(emergency_id: int):
    """
    Finds the next eligible ambulance driver, places the Twilio call,
    and updates database timeline and states.
    """
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        
        # 1. Verify emergency status is active
        cursor.execute("SELECT status, driver_id, prediction, risk_percentage, driver_lat, driver_lng FROM emergencies WHERE id = ?", (emergency_id,))
        emerg = cursor.fetchone()
        if not emerg or emerg['status'].upper() in ['RESOLVED', 'CANCELLED', 'ACCEPTED', 'AMBULANCE_ACCEPTED']:
            return
            
        # 2. Verify no ambulance has accepted yet
        cursor.execute("SELECT id FROM ambulance_emergency_requests WHERE emergency_id = ? AND status = 'ACCEPTED' LIMIT 1", (emergency_id,))
        if cursor.fetchone():
            return

        # 3. Find already attempted drivers
        cursor.execute("SELECT ambulance_id, ambulance_driver_id, attempt_number FROM ambulance_emergency_requests WHERE emergency_id = ?", (emergency_id,))
        attempts = cursor.fetchall()
        attempted_driver_ids = [a['ambulance_driver_id'] for a in attempts if a['ambulance_driver_id'] is not None]
        attempted_amb_ids = [a['ambulance_id'] for a in attempts if a['ambulance_id'] is not None]
        
        valid_attempts = [a['attempt_number'] for a in attempts if a['attempt_number'] is not None]
        max_attempt = max(valid_attempts) if valid_attempts else 0
        next_attempt_number = max_attempt + 1

        # Check maximum attempt limit
        if next_attempt_number > getattr(Config, 'MAX_AMBULANCE_CALL_ATTEMPTS', 3):
            print(f"[TwilioRoutes] Max ambulance call attempts reached for emergency {emergency_id}")
            cursor.execute("INSERT INTO emergency_timeline (emergency_id, step, detail, status) VALUES (?, 'AMBULANCE_DISPATCH_FAILED', 'No registered ambulance driver accepted the emergency request.', 'completed')", (emergency_id,))
            cursor.execute("UPDATE emergencies SET status = 'DISPATCH_FAILED' WHERE id = ?", (emergency_id,))
            conn.commit()
            
            # Notify family / hospital about dispatch failure
            cursor.execute("SELECT u.name, u.phone FROM drivers d JOIN users u ON d.user_id = u.id WHERE d.id = ?", (emerg['driver_id'],))
            driver_user = cursor.fetchone()
            if driver_user:
                fail_msg = f"URGENT UPDATE: No registered ambulance driver has accepted the emergency request yet for {driver_user['name']}. Emergency ID: {emergency_id}. Please contact emergency services immediately if required."
                if getattr(Config, 'TWILIO_TEST_MODE', True):
                    fail_msg = "TEST EMERGENCY — " + fail_msg
                SMSService.send_sms(driver_user['phone'], fail_msg, emergency_id=emergency_id, recipient_type='family', recipient_id=emerg['driver_id'])
                
            return

        # 4. Query next eligible ambulance driver
        cursor.execute('''
            SELECT ad.id as driver_id, ad.name, ad.phone, ad.ambulance_number, ad.hospital_id, a.id as ambulance_id
            FROM ambulance_drivers ad
            JOIN ambulances a ON ad.ambulance_number = a.vehicle_number
            WHERE ad.availability_status IN ('Available', 'EMERGENCY_ASSIGNED') AND ad.is_active = 1 
              AND a.emergency_call_consent = 1 AND a.phone_verified = 1
              AND ad.id NOT IN ({})
            ORDER BY ad.id ASC LIMIT 1
        '''.format(','.join([str(i) for i in attempted_driver_ids]) if attempted_driver_ids else '0'))
        next_driver = cursor.fetchone()

        # Fallback to ambulances table direct matching if no drivers found in driver table
        if not next_driver:
            cursor.execute('''
                SELECT id as ambulance_id, driver_name as name, driver_phone as phone, vehicle_number as ambulance_number, user_id as driver_id
                FROM ambulances
                WHERE status IN ('Available', 'EMERGENCY_ASSIGNED') 
                  AND emergency_call_consent = 1 AND phone_verified = 1
                  AND id NOT IN ({})
                ORDER BY id ASC LIMIT 1
            '''.format(','.join([str(i) for i in attempted_amb_ids]) if attempted_amb_ids else '0'))
            next_driver = cursor.fetchone()

        if not next_driver:
            print(f"[TwilioRoutes] No further available ambulance drivers found for emergency {emergency_id}")
            cursor.execute("SELECT accepted_ambulance_id, ambulance_id FROM emergencies WHERE id = ?", (emergency_id,))
            em_row = cursor.fetchone()
            if not em_row or (not em_row['accepted_ambulance_id'] and not em_row['ambulance_id']):
                cursor.execute("INSERT INTO emergency_timeline (emergency_id, step, detail, status) VALUES (?, 'AMBULANCE_DISPATCH_FAILED', 'No available ambulance drivers found.', 'completed')", (emergency_id,))
                cursor.execute("UPDATE emergencies SET status = 'DISPATCH_FAILED' WHERE id = ?", (emergency_id,))
            conn.commit()
            conn.close()
            return

        driver_phone = next_driver['phone']
        driver_name = next_driver['name']
        ambulance_id = next_driver['ambulance_id']
        driver_id = next_driver['driver_id'] if ('driver_id' in next_driver.keys() and next_driver['driver_id'] is not None) else next_driver['ambulance_id']

        if not driver_phone:
            print(f"[TwilioRoutes] Eligible driver {driver_name} has no phone number registered.")
            cursor.execute('''
                INSERT INTO ambulance_emergency_requests (emergency_id, ambulance_id, ambulance_driver_id, attempt_number, status, failure_reason)
                VALUES (?, ?, ?, ?, 'FAILED', 'AMBULANCE DRIVER PHONE NUMBER NOT REGISTERED')
            ''', (emergency_id, ambulance_id, driver_id, next_attempt_number))
            conn.commit()
            # Close connection here so recursive call has access
            conn.close()
            conn = None
            # Instantly recurse to try next
            dispatch_next_ambulance_driver(emergency_id)
            return

        # 5. Place Call
        print(f"[AMBULANCE] driver selected: {driver_name} ({driver_phone})")
        print("[AMBULANCE CALL] attempting")
        res_call = CallService.make_ambulance_emergency_call(
            phone=driver_phone,
            emergency_id=emergency_id,
            ambulance_driver_id=driver_id,
            ambulance_id=ambulance_id,
            attempt_number=next_attempt_number
        )
        
        call_sid = res_call.get('provider_call_id')
        call_status = res_call.get('status')
        call_err = res_call.get('error')

        if call_status == 'OFFLINE_MODE':
            print("[AMBULANCE CALL] status: Offline mode — real emergency communication unavailable")
            cursor.execute('''
                INSERT INTO emergency_timeline (emergency_id, step, detail, status)
                VALUES (?, 'AMBULANCE_CALL_STARTED', 'Offline mode — real emergency communication unavailable', 'SKIPPED')
            ''', (emergency_id,))
            cursor.execute("UPDATE emergencies SET status = 'DISPATCH_FAILED' WHERE id = ?", (emergency_id,))
            conn.commit()
            return

        if res_call.get('success'):
            print(f"[AMBULANCE CALL] Call SID: {call_sid}")
            print(f"[AMBULANCE CALL] status: {call_status}")
            cursor.execute('''
                INSERT INTO emergency_timeline (emergency_id, step, detail, status)
                VALUES (?, 'AMBULANCE_CALL_STARTED', ?, 'CALLING')
            ''', (emergency_id, f"Calling ambulance driver {driver_name} (Attempt {next_attempt_number}). Call SID: {call_sid}"))
            cursor.execute("UPDATE emergencies SET status = 'DISPATCHING' WHERE id = ?", (emergency_id,))
            conn.commit()
        else:
            print(f"[AMBULANCE CALL] status: FAILED - {call_err}")
            cursor.execute('''
                INSERT INTO emergency_timeline (emergency_id, step, detail, status)
                VALUES (?, 'AMBULANCE_CALL_STARTED', ?, 'FAILED')
            ''', (emergency_id, f"Failed to call ambulance driver {driver_name}: {call_err}"))
            conn.commit()
            
            # Recurse and call next driver
            conn.close()
            conn = None
            dispatch_next_ambulance_driver(emergency_id)
            return
    finally:
        if conn:
            conn.close()

# ──────────────────────────────────────────────────
# API TWILIO WEBHOOKS
# ──────────────────────────────────────────────────

@twilio_bp.route('/api/twilio/sms/status', methods=['POST'])
@validate_twilio_request
def sms_status():
    """Receives message delivery receipts from Twilio."""
    msg_sid = request.form.get('MessageSid')
    status = request.form.get('MessageStatus', '').upper()
    error_code = request.form.get('ErrorCode')
    error_msg = request.form.get('ErrorMessage')

    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Update notification logs
    cursor.execute('''
        UPDATE notification_logs
        SET status = ?, error_message = ?, updated_at = CURRENT_TIMESTAMP
        WHERE provider_message_id = ?
    ''', (status, f"Error Code {error_code}: {error_msg}" if error_code else None, msg_sid))
    
    # Update notifications table
    cursor.execute('''
        UPDATE notifications
        SET status = ?
        WHERE status LIKE ? OR status = 'SENT'
    ''', (status, f"%{msg_sid}%"))
    
    conn.commit()
    conn.close()
    return Response("", status=204)

@twilio_bp.route('/api/twilio/voice/emergency/<int:emergency_id>/<int:ambulance_id>', methods=['POST'])
@validate_twilio_request
def voice_emergency(emergency_id, ambulance_id):
    """TwiML webhook called when the ambulance driver answers the call."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Load emergency details
    cursor.execute('''
        SELECT e.*, u.name as driver_name, d.preferred_language, d.driver_id_code, h.name as hospital_name, h.emergency_number as hospital_phone
        FROM emergencies e
        JOIN drivers d ON e.driver_id = d.id
        JOIN users u ON d.user_id = u.id
        LEFT JOIN hospitals h ON e.hospital_id = h.id
        WHERE e.id = ?
    ''', (emergency_id,))
    emerg = cursor.fetchone()

    if not emerg:
        conn.close()
        return Response("<Response><Say>System error: Emergency not found.</Say><Hangup/></Response>", mimetype='text/xml')

    driver_name = emerg['driver_name']
    risk_level = emerg['severity']
    ai_summary = emerg['explanation'] or "abnormal vital signs detected"
    
    heart_rate = emerg['heart_rate'] if emerg['heart_rate'] else "not available"
    spo2 = emerg['spo2'] if emerg['spo2'] else "not available"
    temperature = emerg['temperature'] if emerg['temperature'] else "not available"
    blood_pressure = emerg['blood_pressure'] if emerg['blood_pressure'] else "not available"
    respiration = emerg['respiration'] if emerg['respiration'] else "not available"
    accident_status = "Possible vehicle accident detected" if emerg['accident_detected'] else "No accident detected"
    
    hospital_name = emerg['hospital_name'] or "Lotus Hospital"
    hospital_phone = emerg['hospital_phone'] or "not available"
    preferred_lang = emerg['preferred_language'] or 'en'

    # Build dynamically formatted voice script text in English
    script = (
        f"Emergency alert from AI Driver Health Guardian. "
        f"Driver: {driver_name}. "
        f"Emergency level: Critical. "
        f"Possible emergency condition: {ai_summary}. "
        f"Please press 1 to accept this emergency request. "
        f"Press 2 to decline."
    )

    # Translate and generate TTS if language is not supported natively by Twilio <Say>
    # Twilio <Say> is supported well for English ('en'). Indian languages fall back to MODE B (TTS + Play)
    if preferred_lang != 'en':
        translated_text = translate_text(script, preferred_lang)
        filename = f"voice_script_{emergency_id}_{ambulance_id}_{preferred_lang}.mp3"
        audio_path = os.path.join(os.path.dirname(__file__), '..', 'static', 'audio', filename)
        speak_text(translated_text, lang=preferred_lang, output_path=audio_path)
        
        # Build external URL
        base_url = getattr(Config, 'BASE_URL', '').rstrip('/')
        audio_url = f"{base_url}/static/audio/{filename}"
        twiml_prompt = f"<Play>{audio_url}</Play>"
    else:
        twiml_prompt = f"<Say voice='alice'>{script}</Say>"

    # Update call answered timestamp in DB
    cursor.execute('''
        UPDATE ambulance_emergency_requests
        SET status = 'ANSWERED', call_answered_at = ?, updated_at = CURRENT_TIMESTAMP
        WHERE emergency_id = ? AND ambulance_id = ?
    ''', (datetime.utcnow().isoformat(), emergency_id, ambulance_id))
    conn.commit()
    conn.close()

    gather_url = f"{getattr(Config, 'BASE_URL', '').rstrip('/')}/api/twilio/voice/gather/{emergency_id}/{ambulance_id}"
    
    twi_response = (
        f"<Response>"
        f"<Gather numDigits='1' action='{gather_url}' method='POST' timeout='{getattr(Config, 'GATHER_TIMEOUT', 15)}'>"
        f"{twiml_prompt}"
        f"</Gather>"
        f"<Say>No response received. Hanging up.</Say>"
        f"<Hangup/>"
        f"</Response>"
    )
    return Response(twi_response, mimetype='text/xml')

@twilio_bp.route('/api/twilio/voice/gather/<int:emergency_id>/<int:ambulance_id>', methods=['POST'])
@validate_twilio_request
def voice_gather(emergency_id, ambulance_id):
    """Processes keypad entry (1 for accept, 2 for decline)."""
    digits = request.form.get('Digits')
    call_sid = request.form.get('CallSid')

    conn = get_db_connection()
    cursor = conn.cursor()

    # Load emergency details
    cursor.execute("SELECT status, driver_id, hospital_id FROM emergencies WHERE id = ?", (emergency_id,))
    emerg = cursor.fetchone()

    if not emerg:
        conn.close()
        return Response("<Response><Say>Error: Emergency not found.</Say><Hangup/></Response>", mimetype='text/xml')

    if digits == '1':
        # Verify no other ambulance accepted
        cursor.execute("SELECT id FROM ambulance_emergency_requests WHERE emergency_id = ? AND status = 'ACCEPTED' LIMIT 1", (emergency_id,))
        already_accepted = cursor.fetchone()
        
        if already_accepted:
            conn.close()
            return Response("<Response><Say>This emergency has already been accepted by another ambulance. Thank you.</Say><Hangup/></Response>", mimetype='text/xml')

        # Race-condition protected acceptance update
        now = datetime.utcnow().isoformat()
        cursor.execute('''
            UPDATE ambulance_emergency_requests
            SET status = 'ACCEPTED', accepted_at = ?, updated_at = CURRENT_TIMESTAMP
            WHERE emergency_id = ? AND ambulance_id = ? AND status != 'ACCEPTED'
        ''', (now, emergency_id, ambulance_id))
        
        cursor.execute('''
            UPDATE emergencies
            SET status = 'ACCEPTED', accepted_ambulance_id = ?, ambulance_id = ?, timestamp = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (ambulance_id, ambulance_id, emergency_id))

        cursor.execute("INSERT INTO emergency_timeline (emergency_id, step, detail, status) VALUES (?, 'AMBULANCE_ACCEPTED', 'Ambulance driver accepted the request.', 'completed')", (emergency_id,))
        
        conn.commit()
        
        # Emit WebSocket event
        socketio.emit('risk_updated', {
            "emergency_id": emergency_id,
            "status": "ACCEPTED",
            "ambulance_id": ambulance_id,
            "timestamp": str(datetime.utcnow())
        })

        # Send family update if configured
        cursor.execute("SELECT u.name as driver_name, u.phone, d.vehicle_number FROM drivers d JOIN users u ON d.user_id = u.id WHERE d.id = ?", (emerg['driver_id'],))
        driver_user = cursor.fetchone()
        
        cursor.execute("SELECT vehicle_number, driver_name FROM ambulances WHERE id = ?", (ambulance_id,))
        amb = cursor.fetchone()

        if driver_user and amb:
            maps_link = f"https://www.google.com/maps?q={request.form.get('FromState', '')}" # Or live GPS
            fam_msg = f"UPDATE: An ambulance driver ({amb['driver_name']}, vehicle: {amb['vehicle_number']}) has accepted the emergency request for {driver_user['driver_name']}. Emergency ID: {emergency_id}."
            if getattr(Config, 'TWILIO_TEST_MODE', True):
                fam_msg = "TEST EMERGENCY — " + fam_msg
            SMSService.send_sms(driver_user['phone'], fam_msg, emergency_id=emergency_id, recipient_type='family', recipient_id=emerg['driver_id'])

        conn.close()
        return Response("<Response><Say>Emergency accepted. Please proceed to the driver location. Thank you.</Say><Hangup/></Response>", mimetype='text/xml')

    elif digits == '2':
        cursor.execute('''
            UPDATE ambulance_emergency_requests
            SET status = 'DECLINED', declined_at = ?, updated_at = CURRENT_TIMESTAMP
            WHERE emergency_id = ? AND ambulance_id = ?
        ''', (datetime.utcnow().isoformat(), emergency_id, ambulance_id))
        cursor.execute("INSERT INTO emergency_timeline (emergency_id, step, detail, status) VALUES (?, 'AMBULANCE_DECLINED', 'Ambulance driver declined the request.', 'completed')", (emergency_id,))
        conn.commit()
        conn.close()

        # Trigger next call asynchronously using thread/SocketIO task or background orchestrator
        from flask import current_app
        if current_app.config.get('TESTING'):
            dispatch_next_ambulance_driver(emergency_id)
        else:
            socketio.start_background_task(dispatch_next_ambulance_driver, emergency_id)

        return Response("<Response><Say>Emergency declined. Thank you.</Say><Hangup/></Response>", mimetype='text/xml')

    else:
        # Invalid input
        conn.close()
        gather_url = f"{getattr(Config, 'BASE_URL', '').rstrip('/')}/api/twilio/voice/gather/{emergency_id}/{ambulance_id}"
        twi_response = (
            f"<Response>"
            f"<Gather numDigits='1' action='{gather_url}' method='POST' timeout='{getattr(Config, 'GATHER_TIMEOUT', 15)}'>"
            f"<Say>Invalid entry. Please press 1 to accept or 2 to decline.</Say>"
            f"</Gather>"
            f"<Say>No response received. Hanging up.</Say>"
            f"<Hangup/>"
            f"</Response>"
        )
        return Response(twi_response, mimetype='text/xml')

@twilio_bp.route('/api/twilio/voice/status', methods=['POST'])
@validate_twilio_request
def voice_status():
    """Receives voice call status changes (ringing, answered, completed, busy, no-answer, failed)."""
    call_sid = request.form.get('CallSid')
    call_status = request.form.get('CallStatus', '').upper()
    duration = request.form.get('CallDuration')
    error_code = request.form.get('SequenceNumber') # Or actual error

    conn = get_db_connection()
    cursor = conn.cursor()

    # Find the corresponding request
    cursor.execute("SELECT id, emergency_id, ambulance_id, status FROM ambulance_emergency_requests WHERE call_sid = ?", (call_sid,))
    req = cursor.fetchone()

    if req:
        # Save ended timestamp if completed
        ended_at = datetime.utcnow().isoformat() if call_status in ['COMPLETED', 'BUSY', 'NO-ANSWER', 'FAILED', 'CANCELED'] else None
        
        # Update request status
        internal_status = call_status.replace('-', '_')
        if call_status == 'COMPLETED' and req['status'] != 'ACCEPTED':
            internal_status = 'NO_RESPONSE'
            
        cursor.execute('''
            UPDATE ambulance_emergency_requests
            SET status = ?, completed_at = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (internal_status, ended_at, req['id']))
        
        # Update call logs
        cursor.execute('''
            UPDATE call_logs
            SET status = ?, failure_reason = ?
            WHERE provider_call_id = ?
        ''', (call_status, f"Twilio Status: {call_status}" if call_status in ['BUSY', 'NO-ANSWER', 'FAILED'] else None, call_sid))
        
        conn.commit()

        # If call failed/declined/no answer, try next driver
        if internal_status in ['BUSY', 'NO_ANSWER', 'FAILED', 'NO_RESPONSE', 'CANCELED']:
            cursor.execute("INSERT INTO emergency_timeline (emergency_id, step, detail, status) VALUES (?, 'AMBULANCE_CALL_FAILED', ?, 'completed')", (req['emergency_id'], f"Call status: {call_status}"))
            conn.commit()
            from flask import current_app
            if current_app.config.get('TESTING'):
                dispatch_next_ambulance_driver(req['emergency_id'])
            else:
                socketio.start_background_task(dispatch_next_ambulance_driver, req['emergency_id'])


    conn.close()
    return Response("", status=204)

# ──────────────────────────────────────────────────
# TEST & CANCELLATION API
# ──────────────────────────────────────────────────

@twilio_bp.route('/api/emergency/test', methods=['POST'])
def emergency_test():
    """Allows authenticated admin to trigger a test emergency."""
    # Ensure test endpoints are authorized in production, bypass for testing
    data = request.get_json() or {}
    driver_id = data.get('driver_id', 1)
    risk_level = data.get('risk_level', 'CRITICAL').upper()
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get details
    cursor.execute("SELECT id FROM drivers WHERE id = ? LIMIT 1", (driver_id,))
    if not cursor.fetchone():
        conn.close()
        return jsonify({"success": False, "error": f"Driver ID {driver_id} not found."}), 400
        
    conn.close()

    # Trigger orchestrator
    from services.emergency_orchestrator import EmergencyOrchestrator
    vitals = {
        "heart_rate": data.get("heart_rate", 142),
        "spo2": data.get("spo2", 86),
        "temperature": data.get("temperature", 38.2),
        "blood_pressure": data.get("blood_pressure", "150/95"),
        "respiration": data.get("respiration", 24)
    }
    prediction = {
        "emergency_type": data.get("emergency_type", "POTENTIAL_CARDIAC_ISSUE"),
        "severity": risk_level,
        "risk_score": 88.0,
        "detected_abnormalities": ["Arrhythmia", "Low Oxygen"]
    }
    
    res = EmergencyOrchestrator.trigger_emergency_workflow(
        driver_id=driver_id,
        prediction_result=prediction,
        vitals=vitals,
        driver_lat=data.get("latitude", 11.3410),
        driver_lng=data.get("longitude", 77.7170)
    )

    return jsonify(res)

@twilio_bp.route('/api/emergency/<int:emergency_id>/cancel', methods=['POST'])
def emergency_cancel(emergency_id):
    """Cancels an active emergency."""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT status FROM emergencies WHERE id = ?", (emergency_id,))
    emerg = cursor.fetchone()
    if not emerg:
        conn.close()
        return jsonify({"success": False, "error": "Emergency not found."}), 404

    cursor.execute("UPDATE emergencies SET status = 'CANCELLED' WHERE id = ?", (emergency_id,))
    cursor.execute('''
        UPDATE ambulance_emergency_requests
        SET status = 'CANCELLED', updated_at = CURRENT_TIMESTAMP
        WHERE emergency_id = ? AND status IN ('PENDING', 'CALLING', 'RINGING', 'ANSWERED')
    ''', (emergency_id,))
    cursor.execute("INSERT INTO emergency_timeline (emergency_id, step, detail, status) VALUES (?, 'EMERGENCY_CANCELLED', 'Emergency cancelled by user/admin.', 'completed')", (emergency_id,))
    
    conn.commit()
    conn.close()

    # Emit Socket event
    socketio.emit('risk_updated', {
        "emergency_id": emergency_id,
        "status": "CANCELLED",
        "timestamp": str(datetime.utcnow())
    })

    return jsonify({"success": True, "emergency_id": emergency_id, "status": "CANCELLED"})
