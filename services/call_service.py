import os
from datetime import datetime
from database import get_db_connection
from config import Config
from services.twilio_service import TwilioService

class CallService:
    @staticmethod
    def initiate_call(phone: str, recipient_role: str, emergency_id: int = None, announcement_text: str = None) -> dict:
        """
        Initiates outbound voice call and logs transaction in call_logs table.
        Simplified version for compatibility.
        Enforces strict consent checks before calling.
        """
        # STRICT CONSENT CHECK LAYER
        if recipient_role:
            conn = get_db_connection()
            cursor = conn.cursor()
            has_consent = False
            is_verified = False
            
            try:
                if recipient_role == 'family':
                    # Phone needs to be mapped to family_member if recipient_id not passed, use phone lookup
                    cursor.execute("SELECT emergency_sms_consent, emergency_status_consent, phone_verified FROM family_members WHERE phone = ? LIMIT 1", (phone,))
                    row = cursor.fetchone()
                    if row:
                        has_consent = (row['emergency_sms_consent'] == 1 or row['emergency_status_consent'] == 1)
                        is_verified = row['phone_verified'] == 1
                elif recipient_role == 'hospital':
                    cursor.execute("SELECT emergency_notification_consent, phone_verified FROM hospitals WHERE emergency_phone = ? OR phone = ? OR emergency_number = ? LIMIT 1", (phone, phone, phone))
                    row = cursor.fetchone()
                    if row:
                        has_consent = row['emergency_notification_consent'] == 1
                        is_verified = row['phone_verified'] == 1
                else:
                    has_consent = True
                    is_verified = True
            except Exception as e:
                print(f"[CallService] Consent check error: {e}")
            finally:
                conn.close()

            if not has_consent or not is_verified:
                print(f"[CallService] BLOCKED: No consent or unverified phone for {recipient_role} phone {phone}")
                return {
                    "success": False,
                    "status": "BLOCKED_NO_CONSENT",
                    "provider": "TWILIO_VOICE",
                    "phone": phone,
                    "provider_call_id": None,
                    "failure_reason": "Communication consent not granted or phone unverified."
                }

        client = TwilioService.get_twilio_client()
        from_num = Config.TWILIO_PHONE_NUMBER
        
        is_configured = bool(client and from_num)
        status = "INITIATED" if is_configured else "CALL SERVICE NOT CONFIGURED"
        provider_call_id = f"CALL-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}" if is_configured else None
        failure_reason = None if is_configured else "Call provider credentials not configured in .env"
        
        if is_configured:
            try:
                twiml = f"<Response><Say voice='alice'>{announcement_text or 'Emergency alert. Please check your AI Driver Health Guardian portal.'}</Say></Response>"
                call = client.calls.create(twiml=twiml, to=phone, from_=from_num)
                provider_call_id = call.sid
                status = "RINGING"
            except Exception as e:
                status = "FAILED"
                failure_reason = str(e)
                print(f"[CallService] Call initiation error to {phone}: {e}")

        # Database Logging
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO call_logs (
                    emergency_id, recipient_role, phone, status, provider_call_id, failure_reason
                ) VALUES (?, ?, ?, ?, ?, ?)
            ''', (emergency_id, recipient_role, phone, status, provider_call_id, failure_reason))
            conn.commit()
            conn.close()
        except Exception as ex:
            print(f"[CallService] DB Logging Error: {ex}")

        return {
            "success": status in ["INITIATED", "RINGING", "CONNECTED"],
            "status": status,
            "provider": "TWILIO_VOICE",
            "phone": phone,
            "provider_call_id": provider_call_id,
            "failure_reason": failure_reason
        }

    @staticmethod
    def make_ambulance_emergency_call(phone: str, emergency_id: int, ambulance_driver_id: int, ambulance_id: int, attempt_number: int = 1) -> dict:
        """
        Initiates outbound voice call to an ambulance driver with a dynamic webhook url.
        Tracks the request status in ambulance_emergency_requests and logs in call_logs.
        Enforces consent checks.
        """
        # STRICT CONSENT CHECK LAYER
        conn_check = get_db_connection()
        cursor_check = conn_check.cursor()
        has_consent = False
        is_verified = False
        try:
            cursor_check.execute("SELECT emergency_call_consent, phone_verified FROM ambulances WHERE id = ?", (ambulance_id,))
            row = cursor_check.fetchone()
            if row:
                has_consent = row['emergency_call_consent'] == 1
                is_verified = row['phone_verified'] == 1
        except Exception as e:
            print(f"[CallService] Ambulance Consent check error: {e}")
        finally:
            conn_check.close()
            
        if not has_consent or not is_verified:
            print(f"[CallService] BLOCKED: No consent or unverified phone for Ambulance ID {ambulance_id}")
            return {
                "success": False,
                "status": "BLOCKED_NO_CONSENT",
                "provider_call_id": None,
                "error": "Communication consent not granted or phone unverified."
            }

        base_url = getattr(Config, 'BASE_URL', '').rstrip('/')
        if not base_url:
            error_msg = "BASE_URL is not configured in environment."
            print(f"[CallService] Error: {error_msg}")
            return {"success": False, "error": error_msg, "status": "FAILED"}

        twiml_url = f"{base_url}/api/twilio/voice/emergency/{emergency_id}/{ambulance_id}"
        status_url = f"{base_url}/api/twilio/voice/status"

        print(f"[CallService] Initiating ambulance emergency call to {phone}. URL: {twiml_url}")
        res = TwilioService.initiate_voice_call(phone, twiml_url, status_callback_url=status_url)
        
        success = res.get("success", False)
        status = "CALLING" if success else "FAILED"
        call_sid = res.get("sid")
        error_msg = res.get("error")

        # Database updates
        try:
            conn = get_db_connection()
            cursor = conn.cursor()

            # Insert into call_logs
            cursor.execute('''
                INSERT INTO call_logs (
                    emergency_id, recipient_role, phone, status, provider_call_id, failure_reason
                ) VALUES (?, 'ambulance_driver', ?, ?, ?, ?)
            ''', (emergency_id, phone, status, call_sid, error_msg))

            # Upsert ambulance_emergency_requests record
            cursor.execute('''
                SELECT id FROM ambulance_emergency_requests 
                WHERE emergency_id = ? AND ambulance_id = ?
                LIMIT 1
            ''', (emergency_id, ambulance_id))
            req_row = cursor.fetchone()

            if req_row:
                cursor.execute('''
                    UPDATE ambulance_emergency_requests
                    SET ambulance_driver_id = ?, attempt_number = ?, call_sid = ?, status = ?, call_started_at = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (ambulance_driver_id, attempt_number, call_sid, status, datetime.utcnow().isoformat(), req_row['id']))
            else:
                cursor.execute('''
                    INSERT INTO ambulance_emergency_requests (
                        emergency_id, ambulance_id, ambulance_driver_id, attempt_number, call_sid, status, call_started_at, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                ''', (emergency_id, ambulance_id, ambulance_driver_id, attempt_number, call_sid, status, datetime.utcnow().isoformat()))

            conn.commit()
            conn.close()
        except Exception as ex:
            print(f"[CallService] DB Update Error: {ex}")

        return {
            "success": success,
            "status": status,
            "provider_call_id": call_sid,
            "error": error_msg
        }
