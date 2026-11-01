"""
AI Driver Health Guardian — Emergency Orchestration Engine

9-Step Automated Emergency Workflow:
  1. Generate Emergency ID + lock session
  2. Generate driver voice alert (TTS)
  3. Generate consciousness check audio
  4. Match nearest suitable hospital
  5. Dispatch nearest ambulance
  6. Notify family members (SMS + audio)
  7. Notify hospital (SMS + audio)
  8. Notify ambulance driver (SMS)
  9. Generate timeline and PDF report
"""

import uuid
import math
import json
from datetime import datetime
from database import get_db_connection
from voice_engine import (
    generate_emergency_audio,
    generate_consciousness_check_audio,
    generate_family_notification_audio,
    generate_hospital_notification_audio
)
from llm_engine import (
    classify_required_department,
    is_life_threatening,
    generate_llm_reasoning,
    generate_emergency_action_plan
)
from notification_engine import notify_all, _log_timeline


def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _find_nearest_hospital(driver_lat: float, driver_lng: float, specialty: str) -> tuple:
    """Return (hospital_row, distance_km, eta_min, maps_url)."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM hospitals WHERE availability = 1")
    hospitals = cursor.fetchall()
    conn.close()

    candidates = []
    for h in hospitals:
        types = [t.strip().lower() for t in (h['emergency_types'] or '').split(',')]
        if specialty.lower() in types or 'icu' in types or specialty == 'General':
            dist = haversine(driver_lat, driver_lng, h['latitude'], h['longitude'])
            candidates.append((h, dist))

    if not candidates:
        candidates = [(h, haversine(driver_lat, driver_lng, h['latitude'], h['longitude']))
                      for h in hospitals]

    candidates.sort(key=lambda x: x[1])
    hosp, dist = candidates[0]
    eta = max(3, int((dist / 45.0) * 60))
    maps_url = (f"https://www.google.com/maps/dir/?api=1"
                f"&origin={driver_lat},{driver_lng}"
                f"&destination={hosp['latitude']},{hosp['longitude']}&travelmode=driving")
    return hosp, round(dist, 2), eta, maps_url


def _dispatch_ambulance(driver_lat: float, driver_lng: float) -> tuple:
    """Return (ambulance_row, eta_min, distance_km) or (None, 0, 0)."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM ambulances WHERE status IN ('Available', 'EMERGENCY_ASSIGNED')")
    ambulances = [dict(a) for a in cursor.fetchall()]

    if not ambulances:
        conn.close()
        return None, 0, 0.0

    # Prioritize ones with driver_user_id and sort by distance
    ambulances.sort(key=lambda a: (0 if a.get('driver_user_id') is not None else 1,
                                   haversine(driver_lat, driver_lng, a['latitude'] or 11.2720, a['longitude'] or 77.5920)))
    closest = ambulances[0]
    dist = haversine(driver_lat, driver_lng, closest['latitude'] or 11.2720, closest['longitude'] or 77.5920)
    eta = max(3, int((dist / 40.0) * 60))

    cursor.execute("UPDATE ambulances SET status='Dispatched', eta_minutes=? WHERE id=?",
                   (eta, closest['id']))
    conn.commit()
    conn.close()

    return closest, eta, round(dist, 2)


def trigger_emergency(driver_id: int, prediction_result: dict,
                      vitals: dict, driver_lat: float = 11.2720,
                      driver_lng: float = 77.5920) -> dict:
    """
    Main entry point for the emergency orchestration engine.
    Called by app.py after AI detects a life-threatening condition.

    Returns:
        dict with full emergency session data for the frontend.
    """
    session_id = str(uuid.uuid4())[:12].upper()
    timestamp  = datetime.now().isoformat()

    # ── Load driver + user info ──────────────────────────────────────────────
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM drivers WHERE id = ?', (driver_id,))
    driver = cursor.fetchone()
    cursor.execute('SELECT name FROM users WHERE id = ?', (driver['user_id'],))
    user = cursor.fetchone()
    driver_name   = user['name'] if user else 'Driver'
    driver_lang   = driver['preferred_language'] or 'en'
    driver_age    = driver['age'] or 0
    blood_group   = driver['blood_group'] or 'Unknown'
    conn.close()

    emergency_type = prediction_result.get('prediction', 'Suspected Cardiac Emergency')
    severity       = prediction_result.get('severity', 'CRITICAL')
    confidence     = prediction_result.get('confidence', 0.90)
    risk_pct       = prediction_result.get('risk_percentage', 85.0)

    # ── Step 1: Department + hospital specialty ──────────────────────────────
    dept_info   = classify_required_department(emergency_type)
    specialty   = dept_info['specialty']
    department  = dept_info['dept']

    _log_timeline(0, 'emergency_detected',
                  f"Emergency {session_id}: {emergency_type} ({severity})")

    # ── Step 2: Create emergency record ─────────────────────────────────────
    ai_reasoning  = generate_llm_reasoning(vitals, prediction_result)
    action_plan   = generate_emergency_action_plan(emergency_type, driver_name)

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO emergencies
          (driver_id, prediction, confidence, risk_percentage, severity,
           explanation, suggested_action, status,
           driver_lat, driver_lng, emergency_code, ai_reasoning,
           escalation_level, timestamp)
        VALUES (?, ?, ?, ?, ?, ?, ?, 'Active', ?, ?, ?, ?, 1, ?)
    ''', (
        driver_id,
        emergency_type,
        confidence,
        risk_pct,
        severity,
        prediction_result.get('explanation', 'Emergency condition detected by AI guardian.'),
        prediction_result.get('suggested_action', 'Park vehicle safely and await emergency responders.'),
        driver_lat,
        driver_lng,
        session_id,
        ai_reasoning,
        timestamp
    ))
    emergency_id = cursor.lastrowid
    conn.commit()
    conn.close()

    _log_timeline(emergency_id, 'session_created',
                  f"Emergency session {session_id} created", 'completed')

    # ── Step 3: Driver voice alert ───────────────────────────────────────────
    hosp_name_placeholder = 'the nearest hospital'
    driver_audio = generate_emergency_audio(
        driver_name=driver_name,
        emergency_type=emergency_type,
        hospital_name=hosp_name_placeholder,
        lang=driver_lang,
        session_id=session_id
    )
    consciousness_audio = generate_consciousness_check_audio(
        driver_name=driver_name,
        lang=driver_lang,
        session_id=session_id
    )
    _log_timeline(emergency_id, 'voice_alert_generated',
                  f"Voice alert generated in {driver_lang}: {driver_audio.get('audio_url', 'N/A')}")

    # ── Step 4: Intelligent Capable Hospital Routing ─────────────────────────
    hosp, dist_km, eta_min, maps_url = _find_nearest_hospital(driver_lat, driver_lng, specialty)

    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Identify all capable hospitals
    cursor.execute("SELECT * FROM hospitals WHERE availability = 1")
    all_hospitals = cursor.fetchall()
    capable_hospitals = []
    for h in all_hospitals:
        types = [t.strip().lower() for t in (h['emergency_types'] or '').split(',')]
        if specialty.lower() in types or 'icu' in types or specialty == 'General':
            capable_hospitals.append(h)
    if not capable_hospitals:
        capable_hospitals = list(all_hospitals)

    capable_hospital_ids = [h['id'] for h in capable_hospitals]
    hosp_notified_json = json.dumps(capable_hospital_ids)

    # Insert into hospital_emergency_requests for each capable hospital
    for hid in capable_hospital_ids:
        cursor.execute("""
            INSERT INTO hospital_emergency_requests (emergency_id, hospital_id, status)
            VALUES (?, ?, 'notified')
        """, (emergency_id, hid))

    cursor.execute("UPDATE emergencies SET hospital_id=?, hospital_notified_ids=? WHERE id=?",
                   (hosp['id'], hosp_notified_json, emergency_id))
    conn.commit()
    conn.close()

    hosp_name = hosp['name']
    _log_timeline(emergency_id, 'HOSPITAL_MATCHED',
                  f"Capable Hospitals ({len(capable_hospitals)}): Matched {hosp_name} ({dist_km} km, ETA {eta_min} min)", 'SUCCESS')

    # ── Step 5: Dispatch / Notify Ambulances ───────────────────────────────────
    ambulance, amb_eta, amb_dist = _dispatch_ambulance(driver_lat, driver_lng)

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM ambulances WHERE status IN ('Available', 'EMERGENCY_ASSIGNED')")
    avail_ambs = cursor.fetchall()
    for amb_row in avail_ambs:
        cursor.execute("""
            INSERT INTO ambulance_emergency_requests (emergency_id, ambulance_id, status)
            VALUES (?, ?, 'notified')
        """, (emergency_id, amb_row['id']))

    if ambulance:
        cursor.execute("UPDATE emergencies SET ambulance_id=? WHERE id=?",
                       (ambulance['id'], emergency_id))
        conn.commit()
        conn.close()
        _log_timeline(emergency_id, 'AMBULANCE_DISPATCHED',
                      f"Ambulance {ambulance['vehicle_number']} ({ambulance['driver_name']}) dispatched (ETA {amb_eta} min, {amb_dist} km)", 'DISPATCHED')
    else:
        conn.commit()
        conn.close()
        _log_timeline(emergency_id, 'AMBULANCE_DISPATCHED',
                      'No ambulance available — manual dispatch required', 'warning')

    # Broadcast Real-Time Emergency Trigger Event
    try:
        from event_broadcaster import publish_event
        publish_event('EMERGENCY_TRIGGERED', {
            'emergency_id': emergency_id,
            'driver_id': driver_id,
            'driver_name': driver_name,
            'prediction': emergency_type,
            'severity': severity,
            'capable_hospital_ids': capable_hospital_ids,
            'hospital_name': hosp_name,
            'ambulance_vehicle': ambulance['vehicle_number'] if ambulance else None,
            'timestamp': timestamp
        })
    except Exception as _ev_err:
        print(f"[EmergencyEngine] Event broadcast warning: {_ev_err}")

    # ── Step 6: Generate family audio ────────────────────────────────────────
    family_audios = []

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM drivers WHERE id = ?', (driver_id,))
    driver = cursor.fetchone()
    conn.close()

    for i, (name_key, phone_key, lang_key) in enumerate([
        ('family_member1_name', 'family_member1_phone', 'family_member1_lang'),
        ('family_member2_name', 'family_member2_phone', 'family_member2_lang')
    ], 1):
        fam_lang = driver[lang_key] or 'en'
        fam_name = driver[name_key]
        fam_phone = driver[phone_key]
        if fam_phone:
            audio = generate_family_notification_audio(
                driver_name=driver_name,
                emergency_type=emergency_type,
                hospital_name=hosp_name,
                eta=eta_min,
                lang=fam_lang,
                member_id=str(i)
            )
            family_audios.append({
                'member': i,
                'name': fam_name,
                'phone': fam_phone,
                'lang': fam_lang,
                'audio_url': audio.get('audio_url'),
                'message_en': audio.get('text_en')
            })

    # ── Step 7: Hospital notification audio ──────────────────────────────────
    hosp_audio = generate_hospital_notification_audio(
        driver_name=driver_name,
        age=driver_age,
        blood_group=blood_group,
        emergency_type=emergency_type,
        risk_percent=risk_pct,
        eta=eta_min,
        department=department,
        lang='en'
    )
    _log_timeline(emergency_id, 'hospital_alerted',
                  f"Hospital {hosp_name} notification prepared")

    # ── Step 8: Send all SMS/call notifications ───────────────────────────────
    notif_results = notify_all(emergency_id)
    _log_timeline(emergency_id, 'notifications_sent',
                  f"Notifications: {json.dumps(notif_results)[:200]}")

    # ── Step 9: Store voice log ───────────────────────────────────────────────
    voice_log = json.dumps({
        'driver_alert': driver_audio.get('text_en', ''),
        'consciousness_check': consciousness_audio.get('text_en', ''),
        'family_alerts': [f['message_en'] for f in family_audios],
        'hospital_alert': hosp_audio.get('text_en', '')
    })
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE emergencies SET voice_log=? WHERE id=?",
                   (voice_log, emergency_id))
    conn.commit()
    conn.close()

    _log_timeline(emergency_id, 'emergency_complete',
                  'All emergency steps executed successfully')

    # ── Return full session dict ─────────────────────────────────────────────
    return {
        'success': True,
        'emergency_id': emergency_id,
        'session_id': session_id,
        'timestamp': timestamp,
        'emergency_type': emergency_type,
        'severity': severity,
        'confidence': confidence,
        'risk_percentage': risk_pct,
        'ai_reasoning': ai_reasoning,
        'action_plan': action_plan,
        'department': department,
        'driver_name': driver_name,
        'driver_lang': driver_lang,
        'hospital': {
            'id': hosp['id'],
            'name': hosp_name,
            'address': hosp['address'],
            'phone': hosp['emergency_number'],
            'lat': hosp['latitude'],
            'lng': hosp['longitude'],
            'distance_km': dist_km,
            'eta_min': eta_min,
            'maps_url': maps_url
        },
        'ambulance': {
            'id': ambulance['id'] if ambulance else None,
            'vehicle': ambulance['vehicle_number'] if ambulance else None,
            'driver': ambulance['driver_name'] if ambulance else None,
            'phone': ambulance['driver_phone'] if ambulance else None,
            'eta_min': amb_eta,
            'distance_km': amb_dist
        } if ambulance else None,
        'voice': {
            'driver_alert_url': driver_audio.get('audio_url'),
            'consciousness_check_url': consciousness_audio.get('audio_url'),
            'driver_alert_text': driver_audio.get('text_translated'),
            'hospital_audio_url': hosp_audio.get('audio_url')
        },
        'family_audios': family_audios,
        'notifications': notif_results,
        'maps_url': maps_url
    }


def escalate_emergency(emergency_id: int) -> dict:
    """
    Escalate emergency when driver is unresponsive.
    Updates escalation_level and logs timeline step.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE emergencies
        SET escalation_level = escalation_level + 1,
            consciousness_response = 'no_response'
        WHERE id = ?
    ''', (emergency_id,))
    conn.commit()
    conn.close()

    _log_timeline(emergency_id, 'escalated',
                  'Driver did not respond to consciousness check — emergency escalated',
                  'critical')

    return {'escalated': True, 'emergency_id': emergency_id}
