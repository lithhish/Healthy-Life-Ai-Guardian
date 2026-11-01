"""
AI Driver Health Guardian — Full Emergency Orchestrator Engine

Responsibilities:
  1. Receive AI emergency event & validate inputs
  2. Create DB emergency event record & capture snapshot
  3. Generate structured Emergency PDF / JSON report
  4. Identify emergency specialty category (Cardiology, Pulmonology, Neurology, Trauma)
  5. Disease & capability based hospital matching
  6. Registered hospital ambulance dispatch
  7. 1-3 KM Privacy-Preserving Nearby Driver Alerting (no private medical history exposed)
  8. Linked family notification
  9. SMS dispatching & logging (services/sms_service.py)
 10. Outbound call initiation & logging (services/call_service.py)
 11. WebSocket real-time event broadcasting (Flask-SocketIO)
 12. Timeline tracking & resolution workflow
"""

import math
import json
from datetime import datetime
from database import get_db_connection
from config import Config
from services.sms_service import SMSService
from services.call_service import CallService
from services.hospital_service import ErodeHospitalDiscoveryService, haversine_distance
from notification_engine import _log_timeline
from extensions import socketio

class EmergencyOrchestrator:
    @staticmethod
    def trigger_emergency_workflow(
        driver_id: int,
        prediction_result: dict,
        vitals: dict,
        driver_lat: float = 11.3410,
        driver_lng: float = 77.7170,
        existing_emergency_id: int = None
    ) -> dict:
        """
        Main entry point for executing the full 21-step emergency response workflow.
        """
        conn = get_db_connection()
        cursor = conn.cursor()

        # 1. Fetch Driver & Linked User info
        cursor.execute('''
            SELECT d.id as driver_id, d.driver_id_code, d.user_id, u.name, u.phone, d.blood_group, d.medical_history, d.vehicle_number
            FROM drivers d JOIN users u ON d.user_id = u.id
            WHERE d.id = ? OR d.user_id = ?
        ''', (driver_id, driver_id))
        driver_row = cursor.fetchone()

        driver_name = driver_row['name'] if driver_row else f"Driver {driver_id}"
        driver_phone = driver_row['phone'] if driver_row else ""
        driver_code = driver_row['driver_id_code'] if driver_row else f"DRV-{driver_id:06d}"
        vehicle_num = driver_row['vehicle_number'] if driver_row else "TN-33-AX-1234"
        blood_group = driver_row['blood_group'] if driver_row else "O+"
        medical_hist = driver_row['medical_history'] if driver_row else "None"

        # 2. Emergency Classification & Category Mapping
        emergency_type = prediction_result.get('emergency_type', 'POTENTIAL_CARDIAC_ISSUE')
        severity = prediction_result.get('severity', 'CRITICAL').upper()
        score = prediction_result.get('risk_score', 85.0)

        specialty_target = "Emergency Medicine"
        if "CARDIAC" in emergency_type or "HEART" in emergency_type:
            specialty_target = "Cardiology"
        elif "PULMONARY" in emergency_type or "OXYGEN" in emergency_type:
            specialty_target = "Pulmonology"
        elif "STROKE" in emergency_type or "NEURO" in emergency_type:
            specialty_target = "Neurology"
        elif "ACCIDENT" in emergency_type or "TRAUMA" in emergency_type:
            specialty_target = "Trauma Care"

        existing_active = None
        if existing_emergency_id:
            cursor.execute('SELECT id, emergency_code FROM emergencies WHERE id = ?', (existing_emergency_id,))
            row = cursor.fetchone()
            if row:
                existing_active = dict(row)

        abnormalities = prediction_result.get('detected_abnormalities', [])
        if not abnormalities:
            abnormalities = []
            hr_val = vitals.get('heart_rate', 0)
            spo2_val = vitals.get('spo2', 100)
            temp_val = vitals.get('temperature', 37.0)
            if hr_val > 100 or (hr_val > 0 and hr_val < 60):
                abnormalities.append(f"Abnormal HR ({hr_val} bpm)")
            if spo2_val < 95 and spo2_val > 0:
                abnormalities.append(f"Low SpO₂ ({spo2_val}%)")
            if temp_val > 38.0:
                abnormalities.append(f"Fever ({temp_val}°C)")
            if not abnormalities:
                abnormalities.append("Real-time Vitals Monitoring Active")

        abnorm_str = ", ".join(abnormalities)
        explanation = f"AI Risk Score: {score}/100. Discovered: {abnorm_str}"
        ecg_val = prediction_result.get('ecg_summary') or vitals.get('ecg_summary') or 'Normal'
        accident_val = 1 if 'accident' in emergency_type.lower() or vitals.get('accident_detected') or vitals.get('accident') else 0
        bp_val = vitals.get('blood_pressure') or f"{vitals.get('blood_pressure_sys', 120)}/{vitals.get('blood_pressure_dia', 80)}"

        from database import generate_unique_emergency_id, generate_unique_ambulance_request_id, generate_unique_report_id

        if existing_active:
            emergency_db_id = existing_active['id']
            emergency_code = existing_active['emergency_code'] or f"EMG-{emergency_db_id:06d}"
        else:
            emergency_code = generate_unique_emergency_id(conn)
            cursor.execute('''
                INSERT INTO emergencies (
                    driver_id, prediction, confidence, risk_percentage, severity, explanation, suggested_action,
                    status, hospital_status, ambulance_status, driver_lat, driver_lng, emergency_code, ai_reasoning,
                    heart_rate, spo2, temperature, blood_pressure, respiration, ecg_summary, accident_detected,
                    ai_summary, emergency_type, risk_level,
                    sleep_hours, stress_level, fatigue_score, symptoms
                ) VALUES (?, ?, ?, ?, ?, ?, ?, 'ALERTING', 'WAITING_FOR_HOSPITAL', 'SEARCHING', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                driver_id, emergency_type, 90.0, score, severity, explanation,
                "Park safely, seek urgent emergency evaluation.",
                driver_lat, driver_lng, emergency_code, json.dumps(prediction_result),
                vitals.get('heart_rate'), vitals.get('spo2'), vitals.get('temperature'), bp_val, vitals.get('respiration') or vitals.get('respiration_rate'),
                ecg_val, accident_val, explanation, emergency_type, severity,
                vitals.get('sleep_hours'), vitals.get('stress_level'), vitals.get('fatigue_score'), vitals.get('symptoms')
            ))
            emergency_db_id = cursor.lastrowid

            # Parse blood pressure for health_logs schema (systolic_bp / diastolic_bp)
            bp_parts = str(bp_val or '120/80').split('/')
            sys_bp_val = float(bp_parts[0]) if len(bp_parts) > 0 and bp_parts[0].replace('.', '', 1).isdigit() else 120.0
            dia_bp_val = float(bp_parts[1]) if len(bp_parts) > 1 and bp_parts[1].replace('.', '', 1).isdigit() else 80.0

            # Save live vitals to health_logs for instant report compiler & dashboard synchronization
            cursor.execute('''
                INSERT INTO health_logs (
                    driver_id, heart_rate, spo2, temperature, systolic_bp, diastolic_bp, respiration_rate,
                    sleep_hours, stress_level, fatigue_score, symptoms
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                driver_id,
                vitals.get('heart_rate', 72.0),
                vitals.get('spo2', 98.0),
                vitals.get('temperature', 36.6),
                sys_bp_val,
                dia_bp_val,
                vitals.get('respiration') or vitals.get('respiration_rate') or 18,
                vitals.get('sleep_hours') or 7.0,
                vitals.get('stress_level') or 3.0,
                vitals.get('fatigue_score') or 3.0,
                vitals.get('symptoms') or abnorm_str or 'Emergency Alert Triggered'
            ))
            conn.commit()

        now_local = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        # Log Initial Timeline Step
        print(f"[EMERGENCY] created. Code: {emergency_code}")
        cursor.execute('''
            INSERT INTO emergency_timeline (emergency_id, step, detail, status, timestamp)
            VALUES (?, 'EMERGENCY_ACTIVATED', ?, 'completed', ?)
        ''', (emergency_db_id, f"Critical emergency activated for {driver_name} ({emergency_type}, Score: {score})", now_local))
        conn.commit()

        # 4. Specialty & Capability Based Hospital Matching
        print("[HOSPITAL] searching")
        matched_hospitals = ErodeHospitalDiscoveryService.search_hospitals(
            specialty=specialty_target,
            user_lat=driver_lat,
            user_lng=driver_lng,
            expand_outside_erode=False
        )

        target_hospital = matched_hospitals[0] if matched_hospitals else {
            "id": 1, "name": "Lotus Hospital & Research Centre", "address": "Poondurai Road, Erode",
            "phone": "+91 424 228 2828", "emergency_number": "+91 424 228 2828", "latitude": 11.3410, "longitude": 77.7170,
            "distance_km": 2.4, "travel_time_min": 8, "maps_url": ""
        }

        print("[HOSPITAL] selected")

        # Update emergency record & hospital_emergency_requests table
        cursor.execute("UPDATE emergencies SET hospital_id = ? WHERE id = ?", (target_hospital['id'], emergency_db_id))
        try:
            cursor.execute("INSERT INTO hospital_emergency_requests (emergency_id, hospital_id, status) VALUES (?, ?, 'notified')", (emergency_db_id, target_hospital['id']))
        except Exception:
            pass
        conn.commit()

        # Log Timeline
        hosp_status = 'SUCCESS' if matched_hospitals else 'FAILED'
        cursor.execute('''
            INSERT INTO emergency_timeline (emergency_id, step, detail, status, timestamp)
            VALUES (?, 'HOSPITAL_MATCHED', ?, ?, ?)
        ''', (emergency_db_id, f"Matched Hospital: {target_hospital['name']} ({specialty_target} Dept, {target_hospital['distance_km']} km)", hosp_status, now_local))
        conn.commit()

        # 5. Registered Hospital Ambulance Search & 25 KM Radius Broadcast
        print("[AMBULANCE] Broadcasting emergency dispatch alert to ALL registered ambulance units...")
        cursor.execute("SELECT * FROM ambulances")
        amb_rows = cursor.fetchall()
            
        assigned_ambulance = None
        amb_request_code = None
        notified_ambulances = []

        if amb_rows:
            amb_list = [dict(a) for a in amb_rows]
            for a in amb_list:
                a_lat = a.get('latitude') or 11.3410
                a_lng = a.get('longitude') or 77.7170
                a['distance_km'] = haversine_distance(driver_lat, driver_lng, a_lat, a_lng)

            # Sort by distance (nearest first)
            amb_list.sort(key=lambda a: (0 if a.get('driver_user_id') is not None else 1, a['distance_km']))

            # Broadcast to ALL registered ambulance units
            nearby_ambs = amb_list

            assigned_ambulance = nearby_ambs[0]
            amb_request_code = generate_unique_ambulance_request_id(conn)
            print(f"[AMBULANCE] Broadcasting alert to ALL {len(nearby_ambs)} ambulance units. Primary: {assigned_ambulance.get('vehicle_number')}")

            for amb in nearby_ambs:
                try:
                    req_code = generate_unique_ambulance_request_id(conn)
                    cursor.execute('''
                        INSERT INTO ambulance_requests (
                            request_id_code, emergency_id, driver_id, ambulance_id, hospital_id,
                            latitude, longitude, priority, status
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, 'CRITICAL', 'PENDING')
                    ''', (req_code, emergency_db_id, driver_id, amb['id'], target_hospital['id'], driver_lat, driver_lng))
                    
                    cursor.execute("UPDATE ambulances SET status = 'EMERGENCY_REQUESTED' WHERE id = ?", (amb['id'],))
                    try:
                        cursor.execute("INSERT INTO ambulance_emergency_requests (emergency_id, ambulance_id, status) VALUES (?, ?, 'notified')", (emergency_db_id, amb['id']))
                    except Exception:
                        pass
                    
                    notified_ambulances.append(amb)

                    conn.commit()
                    # Dispatch SMS & Call to each ambulance driver
                    amb_phone = amb.get('driver_phone') or amb.get('phone')
                    if amb_phone:
                        print(f"[AMBULANCE SMS] Dispatching alert to unit {amb.get('vehicle_number')} at {amb_phone}")
                        maps_link = f"https://www.google.com/maps?q={driver_lat},{driver_lng}" if driver_lat else "Location unavailable"
                        amb_msg = (
                            f"URGENT DISPATCH - UNIT {amb.get('vehicle_number')}\n"
                            f"Emergency: {emergency_type} ({severity})\n"
                            f"Patient Loc: {maps_link}\n"
                            f"Destination: {target_hospital['name']}\n"
                            f"Please accept and respond immediately."
                        )
                        SMSService.send_sms(amb_phone, amb_msg, emergency_id=emergency_db_id, recipient_type='ambulance', recipient_id=amb['id'])
                        try:
                            call_txt = f"Emergency dispatch alert for Ambulance Unit {amb.get('vehicle_number')}. Immediate patient pickup required."
                            CallService.initiate_call(amb_phone, recipient_role='ambulance', emergency_id=emergency_db_id, announcement_text=call_txt)
                        except Exception as amb_call_err:
                            print("[AMBULANCE CALL] Notice:", amb_call_err)
                except Exception as amb_loop_err:
                    print("[AMBULANCE] Loop dispatch notice:", amb_loop_err)

            cursor.execute("UPDATE emergencies SET ambulance_id = ?, status = 'AMBULANCE_REQUESTED' WHERE id = ?", (assigned_ambulance['id'], emergency_db_id))
            conn.commit()

            cursor.execute('''
                INSERT INTO emergency_timeline (emergency_id, step, detail, status, timestamp)
                VALUES (?, 'AMBULANCE_REQUESTED', ?, 'completed', ?)
            ''', (emergency_db_id, f"Ambulance Request {amb_request_code} dispatched to {len(notified_ambulances)} nearby units (Primary: {assigned_ambulance['vehicle_number']})", now_local))
        else:
            print("[AMBULANCE] No available ambulance unit found. Status: AMBULANCE_SEARCHING")

            cursor.execute("UPDATE emergencies SET status = 'AMBULANCE_SEARCHING' WHERE id = ?", (emergency_db_id,))
            cursor.execute('''
                INSERT INTO emergency_timeline (emergency_id, step, detail, status, timestamp)
                VALUES (?, 'AMBULANCE_SEARCHING', 'No available ambulance unit currently free. Retrying search...', 'warning', ?)
            ''', (emergency_db_id, now_local))
            conn.commit()

        # 5.5 Report Generation
        report_code = generate_unique_report_id(conn)
        try:
            cursor.execute('''
                INSERT INTO medical_reports (report_id_code, driver_id, emergency_id, hospital_id)
                VALUES (?, ?, ?, ?)
            ''', (report_code, driver_id, emergency_db_id, target_hospital['id']))
            conn.commit()
            print(f"[REPORT] Report generated: {report_code}")
        except Exception as rpt_err:
            print("[REPORT] Warning creating medical_reports row:", rpt_err)
        # Log report ready step
        _log_timeline(emergency_db_id, 'REPORT_READY', f"Report {report_code} generated", 'COMPLETED')

        # 6. Privacy-Preserving 1–3 KM Nearby Driver Alerts
        cursor.execute('''
            SELECT d.id, d.driver_id_code, u.name, u.phone, d.gps_home_lat, d.gps_home_lng
            FROM drivers d JOIN users u ON d.user_id = u.id
            WHERE d.id != ?
        ''', (driver_id,))
        other_drivers = cursor.fetchall()
        notified_nearby_drivers = []

        for od in other_drivers:
            o_lat = od['gps_home_lat'] or 11.3400
            o_lng = od['gps_home_lng'] or 77.7100
            dist_km = haversine_distance(driver_lat, driver_lng, o_lat, o_lng)

            if dist_km <= 3.0: # Within 3 KM radius
                notified_nearby_drivers.append({
                    "driver_id": od['id'],
                    "name": od['name'],
                    "distance_km": round(dist_km, 2)
                })
                # Privacy-preserving alert message (NO sensitive medical history exposed)
                msg = f"EMERGENCY ALERT: Medical emergency detected {round(dist_km, 1)} KM away on route ({target_hospital['name']} destination). Please yield right of way safely."
                conn.commit()
                SMSService.send_sms(od['phone'], msg, emergency_id=emergency_db_id, recipient_type='nearby_driver', recipient_id=od['id'])

        # 7. Family Notifications (Linked via Driver ID / Family Members)
        cursor.execute('''
            SELECT user_id, phone, name, emergency_sms_consent, emergency_status_consent, phone_verified 
            FROM family_members 
            WHERE driver_id = ? AND status = 'ACTIVE'
        ''', (driver_id,))
        family_rows = cursor.fetchall()
        conn.commit()
        conn.close()

        maps_link = f"https://www.google.com/maps?q={driver_lat},{driver_lng}" if driver_lat and driver_lng else "GPS location unavailable"
        
        if not family_rows:
            family_rows = [{
                'user_id': 99,
                'phone': driver_phone or '+919943064577',
                'name': 'Primary Emergency Contact',
                'emergency_sms_consent': 1,
                'emergency_status_consent': 1,
                'phone_verified': 1
            }]

        for fam in family_rows:
            fam_phone = fam['phone']
            if fam_phone:
                print(f"[FAMILY SMS] Dispatching emergency alert to {fam['name']} ({fam_phone})")
                fam_dict = dict(fam)
                res_sms = SMSService.send_family_emergency_sms(
                    phone=fam_phone,
                    driver_name=driver_name,
                    driver_id=driver_code,
                    emergency_id=emergency_db_id,
                    risk_level=severity,
                    ai_summary=explanation,
                    vitals=vitals,
                    maps_link=maps_link,
                    hospital_name=target_hospital['name'],
                    hospital_phone=target_hospital.get('phone') or target_hospital.get('emergency_number') or 'Not available',
                    emergency_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    recipient_id=fam_dict.get('user_id', 99)
                )

                
                sms_status = res_sms.get('status')
                sms_sid = res_sms.get('provider_message_id')
                sms_err = res_sms.get('error')
                
                _log_timeline(emergency_db_id, 'FAMILY_NOTIFIED', f"SMS Dispatched to Family ({fam['name']} - {fam_phone})", 'SENT')
                
                # Initiate Phone Call for Family Alert
                call_text = f"Urgent Emergency alert for driver {driver_name}. Emergency assistance is active and directing to {target_hospital['name']}."
                print(f"[FAMILY CALL] attempting call to {fam_phone}")
                res_call = CallService.initiate_call(fam_phone, recipient_role='family', emergency_id=emergency_db_id, announcement_text=call_text)
                if res_call.get('success'):
                    print(f"[FAMILY CALL] success. SID: {res_call.get('provider_call_id')}")

        # 8. Hospital Emergency Alert Call & SMS
        conn_hosp = get_db_connection()
        cursor_hosp = conn_hosp.cursor()
        cursor_hosp.execute('''
            SELECT emergency_notification_consent, phone_verified, emergency_phone 
            FROM hospitals WHERE id = ?
        ''', (target_hospital['id'],))
        hosp_row = cursor_hosp.fetchone()
        conn_hosp.close()
        
        hosp_phone = (hosp_row['emergency_phone'] if hosp_row and hosp_row['emergency_phone'] else None) or target_hospital.get('phone') or target_hospital.get('emergency_number') or "+919943064577"
        
        hosp_msg = f"CRITICAL PATIENT DISPATCH: Driver {driver_name} ({driver_code}), Age 24, Blood {blood_group}. Emergency: {emergency_type} (Score {score}). Destination: {target_hospital['name']}."
        print(f"[HOSPITAL SMS] attempting to {hosp_phone}")
        res_sms = SMSService.send_sms(hosp_phone, hosp_msg, emergency_id=emergency_db_id, recipient_type='hospital', recipient_id=target_hospital['id'])
        _log_timeline(emergency_db_id, 'HOSPITAL_NOTIFIED', f"SMS Dispatched to Hospital ({target_hospital['name']} - {hosp_phone})", 'SENT')

        CallService.initiate_call(hosp_phone, recipient_role='hospital', emergency_id=emergency_db_id, announcement_text=f"Emergency patient dispatch alert for {target_hospital['name']}.")


        # 8.5 Sequential Voice Dispatch to Ambulance Drivers if CRITICAL
        if severity == 'CRITICAL':
            try:
                from routes.twilio_routes import dispatch_next_ambulance_driver
                if hasattr(socketio, 'server') and socketio.server is not None:
                    socketio.start_background_task(dispatch_next_ambulance_driver, emergency_db_id)
            except Exception as _bg_err:
                print(f"[Orchestrator] Background task dispatch warning: {_bg_err}")

        # Emit real-time events immediately so frontend overlay updates in < 100ms
        ws_payload = {
            "emergency_id": emergency_db_id,
            "driver_name": driver_name,
            "driver_code": driver_code,
            "emergency_type": emergency_type,
            "severity": severity,
            "risk_score": score,
            "latitude": driver_lat,
            "longitude": driver_lng,
            "hospital": target_hospital['name'],
            "ambulance": assigned_ambulance['vehicle_number'] if assigned_ambulance else "TN-33-AMB-108",
            "nearby_drivers_notified": len(notified_nearby_drivers),
            "timestamp": str(datetime.utcnow())
        }

        try:
            from event_broadcaster import publish_event
            publish_event('EMERGENCY_TRIGGERED', ws_payload)
            publish_event('AMBULANCE_REQUESTED', ws_payload)
            if hasattr(socketio, 'server') and socketio.server is not None:
                socketio.emit('emergency_created', ws_payload)
                socketio.emit('risk_updated', ws_payload)
                socketio.emit('ambulance_requested', ws_payload)
        except Exception as ws_err:
            print("WebSocket / SSE emit notice:", ws_err)

        conn.close()
        print("[EMERGENCY] workflow completed in fast path")


        return {
            "success": True,
            "emergency_id": emergency_code,
            "emergency_db_id": emergency_db_id,
            "emergency_code": emergency_code,
            "driver_id": driver_code,
            "driver_name": driver_name,
            "emergency_type": emergency_type,
            "risk_level": severity,
            "severity": severity,
            "risk_score": score,
            "ambulance_request_id": amb_request_code or "REQ-000000",
            "ambulance_status": "REQUESTED" if assigned_ambulance else "SEARCHING",
            "hospital_id": target_hospital.get('hospital_id_code') or f"HOS-{target_hospital['id']:06d}",
            "assigned_hospital": target_hospital,
            "hospital": target_hospital,
            "assigned_ambulance": assigned_ambulance,
            "ambulance": assigned_ambulance or {"vehicle_number": "TN-33-AMB-108", "driver_name": "SANTHOSH S", "driver_phone": "+91 9943064577", "eta_minutes": 5},
            "report_id": report_code,

            "nearby_drivers_notified_count": len(notified_nearby_drivers),
            "report_summary": {
                "driver_code": driver_code,
                "vehicle_number": vehicle_num,
                "blood_group": blood_group,
                "medical_history": medical_hist,
                "detected_abnormalities": prediction_result.get('detected_abnormalities', []),
                "disclaimer": prediction_result.get('disclaimer')
            }
        }

