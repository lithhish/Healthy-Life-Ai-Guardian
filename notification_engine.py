"""
AI Driver Health Guardian — Notification Engine

Pluggable notification adapter with simulated demo mode.
Supports:
  - Simulated call/SMS logs (always active — demo mode)
  - Twilio SMS/Voice (activate via .env: TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_FROM)
  - Exotel (stub — activate via EXOTEL_SID, EXOTEL_TOKEN)

All notifications are logged to the `notifications` DB table regardless of mode.
"""

import os
import uuid
import json
from datetime import datetime
from database import get_db_connection

# ──────────────────────────────────────────────────
# Config
# ──────────────────────────────────────────────────
TWILIO_SID   = os.environ.get('TWILIO_ACCOUNT_SID', '')
TWILIO_TOKEN = os.environ.get('TWILIO_AUTH_TOKEN', '')
TWILIO_FROM  = os.environ.get('TWILIO_FROM', '')
USE_TWILIO   = bool(TWILIO_SID and TWILIO_TOKEN and TWILIO_FROM)

EXOTEL_SID   = os.environ.get('EXOTEL_SID', '')
EXOTEL_TOKEN = os.environ.get('EXOTEL_TOKEN', '')
USE_EXOTEL   = bool(EXOTEL_SID and EXOTEL_TOKEN)


# ──────────────────────────────────────────────────
# DB Logging
# ──────────────────────────────────────────────────
def _log_notification(emergency_id: int, recipient_type: str,
                       recipient_name: str, phone: str,
                       channel: str, message: str, status: str,
                       lang: str = 'en'):
    """Persist notification record to database."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO notifications
              (emergency_id, recipient_type, recipient_name, phone, channel, message, status, lang, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (emergency_id, recipient_type, recipient_name, phone,
              channel, message, status, lang, datetime.now().isoformat()))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[NotifEngine] DB log error: {e}")


def _log_timeline(emergency_id: int, step: str, detail: str, status: str = 'completed'):
    """Log emergency workflow step to timeline table."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO emergency_timeline (emergency_id, step, detail, status, timestamp)
            VALUES (?, ?, ?, ?, ?)
        ''', (emergency_id, step, detail, status, datetime.now().isoformat()))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[NotifEngine] Timeline log error: {e}")


# ──────────────────────────────────────────────────
# SMS Sender
# ──────────────────────────────────────────────────
def send_sms(to_phone: str, message: str, emergency_id: int,
             recipient_type: str, recipient_name: str, lang: str = 'en') -> str:
    """
    Send SMS to a recipient. Returns status string.
    """
    status = 'simulated'

    if USE_TWILIO:
        try:
            from twilio.rest import Client
            client = Client(TWILIO_SID, TWILIO_TOKEN)
            msg = client.messages.create(
                body=message, from_=TWILIO_FROM, to=to_phone
            )
            status = f'sent:{msg.sid}'
            print(f"[NotifEngine] Twilio SMS sent to {to_phone}: {msg.sid}")
        except Exception as e:
            print(f"[NotifEngine] Twilio SMS error: {e}")
            status = f'failed:{str(e)[:60]}'

    elif USE_EXOTEL:
        # Exotel stub — plug in your own API call here
        status = 'exotel_stub'
        print(f"[NotifEngine] Exotel SMS stub — would send to {to_phone}")

    else:
        safe_msg = message[:80].encode('ascii', errors='replace').decode('ascii')
        print(f"[NotifEngine] SIMULATED SMS to {to_phone}: {safe_msg}...")

    _log_notification(emergency_id, recipient_type, recipient_name,
                      to_phone, 'SMS', message, status, lang)
    return status


def make_voice_call(to_phone: str, twiml_message: str, emergency_id: int,
                    recipient_type: str, recipient_name: str, lang: str = 'en') -> str:
    """
    Place an automated voice call. Returns status string.
    """
    status = 'simulated'

    if USE_TWILIO:
        try:
            from twilio.rest import Client
            client = Client(TWILIO_SID, TWILIO_TOKEN)
            twiml = f'<Response><Say language="{lang}" voice="alice">{twiml_message}</Say></Response>'
            call = client.calls.create(
                twiml=twiml, from_=TWILIO_FROM, to=to_phone
            )
            status = f'calling:{call.sid}'
            print(f"[NotifEngine] Twilio CALL to {to_phone}: {call.sid}")
        except Exception as e:
            print(f"[NotifEngine] Twilio call error: {e}")
            status = f'failed:{str(e)[:60]}'
    else:
        print(f"[NotifEngine] SIMULATED CALL to {to_phone}: {twiml_message[:80]}...")

    _log_notification(emergency_id, recipient_type, recipient_name,
                      to_phone, 'CALL', twiml_message, status, lang)
    return status


# ──────────────────────────────────────────────────
# Notification Builders
# ──────────────────────────────────────────────────
def build_sms_message(driver_name: str, emergency_type: str,
                       hospital_name: str, distance_km: float,
                       eta_min: int, lat: float, lng: float,
                       emergency_phone: str, timestamp: str) -> str:
    maps_link = f"https://maps.google.com/?q={lat},{lng}" if lat and lng else "GPS N/A"
    return (
        f"🚨 EMERGENCY ALERT — AI Driver Health Guardian\n"
        f"Patient: {driver_name}\n"
        f"Emergency: {emergency_type}\n"
        f"Hospital: {hospital_name}\n"
        f"Distance: {distance_km} km | ETA: {eta_min} min\n"
        f"GPS: {maps_link}\n"
        f"Emergency No: {emergency_phone}\n"
        f"Time: {timestamp}\n"
        f"Please respond immediately."
    )


def build_hospital_sms(driver_name: str, emergency_type: str,
                        blood_group: str, age: int, risk_pct: float,
                        eta_min: int, lat: float, lng: float) -> str:
    maps_link = f"https://maps.google.com/?q={lat},{lng}" if lat and lng else "GPS N/A"
    return (
        f"🏥 INCOMING EMERGENCY — AI Health Guardian\n"
        f"Patient: {driver_name} | Age: {age} | Blood: {blood_group}\n"
        f"Emergency: {emergency_type} | Risk: {risk_pct}%\n"
        f"ETA: {eta_min} min\n"
        f"GPS: {maps_link}\n"
        f"Prepare emergency team NOW."
    )


# ──────────────────────────────────────────────────
# Master Notification Orchestrator
# ──────────────────────────────────────────────────
def notify_all(emergency_id: int) -> dict:
    """
    Fetch emergency from DB and send all notifications.
    Called by emergency_engine after all DB records are created.
    Returns summary dict.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    # Fetch emergency
    cursor.execute('SELECT * FROM emergencies WHERE id = ?', (emergency_id,))
    emergency = cursor.fetchone()
    if not emergency:
        conn.close()
        return {'error': 'Emergency not found'}

    # Fetch driver + user
    cursor.execute('SELECT * FROM drivers WHERE id = ?', (emergency['driver_id'],))
    driver = cursor.fetchone()
    cursor.execute('SELECT name FROM users WHERE id = ?', (driver['user_id'],))
    user = cursor.fetchone()
    driver_name = user['name'] if user else 'Driver'
    driver_lang = driver['preferred_language'] or 'en'

    # Fetch hospital
    hospital = None
    if emergency['hospital_id']:
        cursor.execute('SELECT * FROM hospitals WHERE id = ?', (emergency['hospital_id'],))
        hospital = cursor.fetchone()

    # Fetch ambulance
    ambulance = None
    if emergency['ambulance_id']:
        cursor.execute('SELECT * FROM ambulances WHERE id = ?', (emergency['ambulance_id'],))
        ambulance = cursor.fetchone()

    conn.close()

    hosp_name    = hospital['name'] if hospital else 'Nearest Hospital'
    hosp_phone   = hospital['emergency_number'] if hospital else 'N/A'
    distance_km  = 0
    eta_min      = 8
    driver_lat   = emergency['driver_lat'] or 11.2720
    driver_lng   = emergency['driver_lng'] or 77.5920
    timestamp    = emergency['timestamp']
    emerg_type   = emergency['prediction']
    risk_pct     = emergency['risk_percentage']
    age          = driver['age'] or 0
    blood_group  = driver['blood_group'] or 'Unknown'

    results = {'family': [], 'hospital': None, 'ambulance': None}

    # ── Family Member 1 ──
    fam1_name  = driver['family_member1_name']
    fam1_phone = driver['family_member1_phone']
    fam1_lang  = driver['family_member1_lang'] or 'en'
    if fam1_phone:
        sms = build_sms_message(driver_name, emerg_type, hosp_name,
                                distance_km, eta_min, driver_lat, driver_lng,
                                hosp_phone, timestamp)
        status1 = send_sms(fam1_phone, sms, emergency_id,
                           'family', fam1_name or 'Family Member 1', fam1_lang)
        results['family'].append({'name': fam1_name, 'phone': fam1_phone, 'status': status1})
        _log_timeline(emergency_id, 'FAMILY_NOTIFIED',
                      f"SMS sent to {fam1_name} ({fam1_phone})", 'SENT')

    # ── Family Member 2 ──
    fam2_name  = driver['family_member2_name']
    fam2_phone = driver['family_member2_phone']
    fam2_lang  = driver['family_member2_lang'] or 'en'
    if fam2_phone:
        sms = build_sms_message(driver_name, emerg_type, hosp_name,
                                distance_km, eta_min, driver_lat, driver_lng,
                                hosp_phone, timestamp)
        status2 = send_sms(fam2_phone, sms, emergency_id,
                           'family', fam2_name or 'Family Member 2', fam2_lang)
        results['family'].append({'name': fam2_name, 'phone': fam2_phone, 'status': status2})

    # ── Hospital ──
    if hospital and hospital['emergency_number']:
        hsms = build_hospital_sms(driver_name, emerg_type, blood_group,
                                   age, risk_pct, eta_min, driver_lat, driver_lng)
        hstatus = send_sms(hospital['emergency_number'], hsms, emergency_id,
                           'hospital', hosp_name, 'en')
        results['hospital'] = {'name': hosp_name, 'status': hstatus}
        _log_timeline(emergency_id, 'HOSPITAL_NOTIFIED',
                      f"SMS sent to {hosp_name} ({hospital['emergency_number']})", 'SENT')

    # ── Ambulance Driver ──
    if ambulance and ambulance['driver_phone']:
        amb_sms = (
            f"🚑 DISPATCH ALERT — AI Guardian\n"
            f"EMERGENCY: {emerg_type}\n"
            f"Patient: {driver_name} | Age: {age} | Blood: {blood_group}\n"
            f"GPS: https://maps.google.com/?q={driver_lat},{driver_lng}\n"
            f"Report to {hosp_name} immediately."
        )
        astatus = send_sms(ambulance['driver_phone'], amb_sms, emergency_id,
                           'ambulance', ambulance['driver_name'], 'en')
        results['ambulance'] = {'driver': ambulance['driver_name'], 'status': astatus}
        _log_timeline(emergency_id, 'AMBULANCE_CALL_STARTED',
                      f"Dispatch alert sent to {ambulance['driver_name']} ({ambulance['driver_phone']})", 'CALLING')

    return results
