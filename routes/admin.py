from flask import Blueprint, request, jsonify, session
from extensions import db
from models import (User, Driver, Family, Hospital, HospitalStaff, Ambulance, 
                    AmbulanceService, EmergencyEvent, HospitalAdmission)
from sqlalchemy import func
from routes.main import admin_required

admin_bp = Blueprint('admin', __name__, url_prefix='/api/admin')

@admin_bp.route('/analytics', methods=['GET'])
@admin_required
def get_analytics():
    try:
        # 1. Total counts
        hospitals_count = Hospital.query.count()
        patients_count = HospitalAdmission.query.count()
        admitted_count = HospitalAdmission.query.filter_by(status='ADMITTED').count()
        discharged_count = HospitalAdmission.query.filter_by(status='DISCHARGED').count()
        
        staff_count = HospitalStaff.query.count()
        doctors_count = HospitalStaff.query.filter_by(staff_role='doctor').count()
        nurses_count = HospitalStaff.query.filter_by(staff_role='nurse').count()
        other_staff_count = staff_count - (doctors_count + nurses_count)
        
        ambulances_count = Ambulance.query.count()
        ambulances_avail = Ambulance.query.filter_by(status='AVAILABLE').count()
        ambulances_busy = ambulances_count - ambulances_avail
        
        emergencies_count = EmergencyEvent.query.count()
        active_emergencies = EmergencyEvent.query.filter_by(status='ACTIVE').count()
        resolved_emergencies = EmergencyEvent.query.filter_by(status='RESOLVED').count()
        
        driver_count = Driver.query.count()
        from database import get_db_connection
        conn_an = get_db_connection()
        c_an = conn_an.cursor()
        c_an.execute("SELECT COUNT(*) FROM family_members")
        family_count = c_an.fetchone()[0]
        c_an.close()

        # 2. Aggregations for charts
        
        # Hospital-wise Patient Count
        hospital_patients = db.session.query(
            Hospital.name, func.count(HospitalAdmission.id)
        ).outerjoin(HospitalAdmission, Hospital.id == HospitalAdmission.hospital_id)\
         .group_by(Hospital.id).all()
        
        # Hospital-wise Staff Count
        hospital_staff = db.session.query(
            Hospital.name, func.count(HospitalStaff.id)
        ).outerjoin(HospitalStaff, Hospital.id == HospitalStaff.hospital_id)\
         .group_by(Hospital.id).all()

        # Emergency Severity
        severity_counts = db.session.query(
            EmergencyEvent.risk_level, func.count(EmergencyEvent.id)
        ).group_by(EmergencyEvent.risk_level).all()

        # Compile data
        data = {
            "counts": {
                "hospitals": hospitals_count,
                "total_patients": patients_count,
                "admitted": admitted_count,
                "discharged": discharged_count,
                "total_staff": staff_count,
                "doctors": doctors_count,
                "nurses": nurses_count,
                "other_staff": other_staff_count,
                "ambulances": ambulances_count,
                "ambulances_available": ambulances_avail,
                "ambulances_busy": ambulances_busy,
                "active_emergencies": active_emergencies,
                "resolved_emergencies": resolved_emergencies,
                "total_emergencies": emergencies_count,
                "drivers": driver_count,
                "families": family_count
            },
            "charts": {
                "hospital_patients": {
                    "labels": [h[0] for h in hospital_patients],
                    "data": [h[1] for h in hospital_patients]
                },
                "hospital_staff": {
                    "labels": [h[0] for h in hospital_staff],
                    "data": [h[1] for h in hospital_staff]
                },
                "staff_roles": {
                    "labels": ["Doctors", "Nurses", "Other"],
                    "data": [doctors_count, nurses_count, other_staff_count]
                },
                "patient_status": {
                    "labels": ["Admitted", "Discharged"],
                    "data": [admitted_count, discharged_count]
                },
                "emergency_severity": {
                    "labels": [s[0] if s[0] else 'Unknown' for s in severity_counts],
                    "data": [s[1] for s in severity_counts]
                },
                "ambulance_status": {
                    "labels": ["Available", "Busy"],
                    "data": [ambulances_avail, ambulances_busy]
                }
            }
        }
        
        return jsonify(data)
        
    except Exception as e:
        print(f"Error fetching analytics: {e}")
        return jsonify({"error": str(e)}), 500

@admin_bp.route('/hospitals', methods=['GET'])
@admin_required
def get_hospitals():
    try:
        from database import get_db_connection
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM hospitals ORDER BY id DESC")
        hospitals = [dict(r) for r in cursor.fetchall()]
        
        results = []
        for h in hospitals:
            h_id = h['id']
            cursor.execute("SELECT COUNT(*) FROM hospital_admissions WHERE hospital_id = ?", (h_id,))
            patient_count = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM doctors WHERE hospital_id = ?", (h_id,))
            doc_count = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM nurses WHERE hospital_id = ?", (h_id,))
            nur_count = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM ambulances WHERE hospital_id = ?", (h_id,))
            amb_count = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM emergencies WHERE (hospital_id = ? OR accepted_hospital_id = ?) AND status = 'ACTIVE'", (h_id, h_id))
            active_emergencies = cursor.fetchone()[0]

            results.append({
                "id": h['id'],
                "hospital_id_code": h.get('hospital_id_code') or f"HOS-{h['id']:06d}",
                "name": h['name'],
                "hospital_type": h.get('hospital_type') or 'Multi-Speciality',
                "phone": h.get('phone') or h.get('emergency_number') or '',
                "email": h.get('email') or '',
                "address": h.get('address') or '',
                "city": h.get('city') or 'Erode',
                "district": h.get('district') or 'Erode',
                "state": h.get('state') or 'Tamil Nadu',
                "pincode": h.get('pincode') or '',
                "latitude": h.get('latitude'),
                "longitude": h.get('longitude'),
                "emergency_available": bool(h.get('emergency_available', 1)),
                "icu_available": bool(h.get('icu_availability', 1)),
                "cardiology_available": bool(h.get('cardiology_availability', 1)),
                "neurology_available": bool(h.get('neurology_availability', 1)),
                "available_beds": h.get('available_beds', 10),
                "icu_beds": h.get('icu_beds', 5),
                "ambulance_available": bool(h.get('ambulance_availability', 1)),
                "patients": patient_count,
                "staff": doc_count + nur_count,
                "ambulances": amb_count,
                "active_emergencies": active_emergencies,
                "status": (h.get('status') or 'ACTIVE').upper()
            })
        conn.close()
        return jsonify({"success": True, "hospitals": results})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@admin_bp.route('/hospitals/<int:hospital_id>', methods=['GET'])
@admin_required
def get_hospital_details(hospital_id):
    try:
        from database import get_db_connection
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM hospitals WHERE id = ?", (hospital_id,))
        h_row = cursor.fetchone()
        if not h_row:
            conn.close()
            return jsonify({"error": "Hospital not found"}), 404
        h = dict(h_row)  # Convert to dict to allow .get() calls

        # Patient count
        cursor.execute("SELECT COUNT(*) as cnt FROM hospital_admissions WHERE hospital_id = ?", (hospital_id,))
        pt = cursor.fetchone()
        patient_count = pt['cnt'] if pt else 0

        # Staff count (all hospital staff users)
        cursor.execute("SELECT COUNT(*) as cnt FROM users WHERE hospital_id = ? AND role IN ('doctor','nurse','receptionist','pharmacist','ambulance_driver','hospital_staff','hospital')", (hospital_id,))
        st = cursor.fetchone()
        staff_count = st['cnt'] if st else 0

        # Ambulance count
        cursor.execute("SELECT COUNT(*) as cnt FROM ambulances WHERE hospital_id = ?", (hospital_id,))
        ab = cursor.fetchone()
        amb_count = ab['cnt'] if ab else 0

        # Active emergencies
        cursor.execute("SELECT COUNT(*) as cnt FROM emergencies WHERE hospital_id = ? AND status = 'ACTIVE'", (hospital_id,))
        em = cursor.fetchone()
        em_count = em['cnt'] if em else 0

        # Staff list
        cursor.execute("""
            SELECT id, name, role, email, phone FROM users
            WHERE hospital_id = ?
            ORDER BY name
        """, (hospital_id,))
        staff_rows = cursor.fetchall()
        staff_list = [{"id": s['id'], "name": s['name'], "role": s['role']} for s in staff_rows]

        conn.close()
        return jsonify({
            "success": True,
            "hospital": {
                "id": h['id'],
                "hospital_id_code": h['hospital_id_code'] or f"HOS-{h['id']:06d}",
                "name": h['name'],
                "hospital_type": h['hospital_type'] or 'Multi-Speciality',
                "phone": h.get('emergency_number') or h.get('phone') or '',
                "email": h['email'] or '',
                "address": h['address'] or '',
                "city": h['city'] or 'Erode',
                "district": h['district'] or 'Erode',
                "state": h['state'] or 'Tamil Nadu',
                "pincode": h['pincode'] or '',
                "latitude": h['latitude'],
                "longitude": h['longitude'],
                "available_beds": h['available_beds'] or 0,
                "icu_beds": h['icu_beds'] or 0,
                "emergency_available": bool(h.get('emergency_available', 1)),
                "icu_available": bool(h.get('icu_availability', 1)),
                "cardiology_available": bool(h.get('cardiology_availability', 1)),
                "neurology_available": bool(h.get('neurology_availability', 1)),
                "ambulance_available": bool(h.get('ambulance_availability', 1)),
                "status": (h['status'] or 'ACTIVE').upper(),
                "total_patients": patient_count,
                "total_staff": staff_count,
                "ambulances": amb_count,
                "active_emergencies": em_count,
                "staff_list": staff_list,
            }
        })
    except Exception as e:
        print("Error getting hospital details:", str(e))
        return jsonify({"error": str(e)}), 500

@admin_bp.route('/register_hospital', methods=['POST'])
@admin_bp.route('/hospitals/create', methods=['POST'])
@admin_required
def register_hospital():
    try:
        from werkzeug.security import generate_password_hash
        from database import get_db_connection, generate_unique_hospital_id
        from geocoding_service import geocode_address_fallback, DEFAULT_LAT, DEFAULT_LNG
        import re

        data = request.json or request.form
        
        name = data.get('name')
        hospital_type = data.get('hospital_type') or 'Multi-Speciality'
        phone = data.get('phone')
        email = data.get('email', '')
        address = data.get('address')
        city = data.get('city') or 'Erode'
        district = data.get('district') or 'Erode'
        state = data.get('state') or 'Tamil Nadu'
        pincode = data.get('pincode', '')
        username = data.get('username')
        password = data.get('password')

        lat = data.get('latitude')
        lon = data.get('longitude')
        
        if not all([name, phone, address, username, password]):
            return jsonify({"error": "Hospital Name, Phone, Address, Admin Username, and Password are required."}), 400

        # Validate Phone Number Format (Indian Phone Validation)
        clean_phone = re.sub(r'[^\d+]', '', str(phone))
        if len(re.sub(r'\D', '', clean_phone)) < 10:
            return jsonify({"error": "Please enter a valid phone number (e.g. +91 9876543210)."}), 400

        # Validate unique username
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
        if cursor.fetchone():
            conn.close()
            return jsonify({"error": f"Username '{username}' already exists."}), 400

        # Automatic Geocoding
        final_lat = float(lat) if lat and str(lat).replace('.', '', 1).replace('-', '', 1).isdigit() else None
        final_lng = float(lon) if lon and str(lon).replace('.', '', 1).replace('-', '', 1).isdigit() else None

        if final_lat is None or final_lng is None:
            full_addr = f"{address}, {city}, {district}, {state}, India"
            geo_result = geocode_address_fallback(full_addr)
            if geo_result:
                final_lat, final_lng = geo_result
            else:
                # Default to Erode Center coordinates if geocoding is unavailable
                final_lat, final_lng = DEFAULT_LAT, DEFAULT_LNG

        # Generate Unique Hospital ID (Format: HOS-000001)
        hospital_code = generate_unique_hospital_id(conn)

        # 1. Create Base User Account for Hospital Admin
        hashed_pw = generate_password_hash(password, method='pbkdf2:sha256')
        cursor.execute('''
            INSERT INTO users (username, password, role, name, phone, email, verified)
            VALUES (?, ?, 'hospital', ?, ?, ?, 1)
        ''', (username, hashed_pw, f"{name} Admin", phone, email))
        user_id = cursor.lastrowid

        # 2. Insert into Hospitals Table (emergency_number is the phone field)
        emergency_notification_consent = 1 if str(data.get('emergency_notification_consent')).lower() in ['true', '1', 'on'] else 0
        emergency_phone = data.get('emergency_phone') or phone
        emergency_email = data.get('emergency_email') or email
        notification_enabled = emergency_notification_consent
        
        # Check if phone is verified
        cursor.execute("SELECT is_verified FROM otp_verifications WHERE phone = ? AND purpose = 'hospital_reg' ORDER BY id DESC LIMIT 1", (emergency_phone,))
        otp_record = cursor.fetchone()
        phone_verified = 1 if otp_record and otp_record['is_verified'] == 1 else 0

        cursor.execute('''
            INSERT INTO hospitals (
                hospital_id_code, name, hospital_type, emergency_number, email, address,
                city, district, state, pincode, latitude, longitude,
                emergency_available, icu_availability, cardiology_availability, neurology_availability,
                available_beds, icu_beds, ambulance_availability, status, username, password,
                emergency_notification_consent, emergency_phone, emergency_email, notification_enabled, phone_verified, consent_timestamp
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'ACTIVE', ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ''', (
            hospital_code, name, hospital_type, phone, email, address,
            city, district, state, pincode, final_lat, final_lng,
            1 if data.get('emergency_available', True) else 0,
            1 if data.get('icu_available', True) else 0,
            1 if data.get('cardiology_available', True) else 0,
            1 if data.get('neurology_available', True) else 0,
            int(data.get('available_beds', 10)),
            int(data.get('icu_beds', 5)),
            1 if data.get('ambulance_available', True) else 0,
            username, hashed_pw,
            emergency_notification_consent, emergency_phone, emergency_email, notification_enabled, phone_verified
        ))
        hospital_id = cursor.lastrowid

        # Log consent audit
        cursor.execute('''
            INSERT INTO consent_audit_logs (entity_id, entity_type, consent_type, new_value, changed_by, reason)
            VALUES (?, 'Hospital', 'Emergency Notification', ?, ?, 'Initial Registration')
        ''', (hospital_id, 'TRUE' if emergency_notification_consent else 'FALSE', username))

        # Link hospital_id in users
        cursor.execute("UPDATE users SET hospital_id = ? WHERE id = ?", (hospital_id, user_id))
        conn.commit()
        conn.close()

        return jsonify({
            "success": True,
            "message": f"Hospital '{name}' registered successfully with ID {hospital_code}.",
            "hospital_id": hospital_id,
            "hospital_id_code": hospital_code
        }), 201
        
    except Exception as e:
        print("Error registering hospital:", str(e))
        return jsonify({"error": str(e)}), 500


@admin_bp.route('/search_drivers', methods=['GET'])
@admin_required
def search_drivers_api():
    try:
        from database import get_db_connection
        q = request.args.get('q', '').strip()
        conn = get_db_connection()
        cursor = conn.cursor()
        if q:
            like_q = f"%{q}%"
            cursor.execute('''
                SELECT d.id, d.driver_id_code, COALESCE(d.name, u.name) as name,
                       COALESCE(d.phone, u.phone) as phone, d.vehicle_number
                FROM drivers d
                LEFT JOIN users u ON d.user_id = u.id
                WHERE d.driver_id_code LIKE ? OR d.name LIKE ? OR u.name LIKE ? OR d.phone LIKE ? OR u.phone LIKE ?
                ORDER BY d.id DESC LIMIT 20
            ''', (like_q, like_q, like_q, like_q, like_q))
        else:
            cursor.execute('''
                SELECT d.id, d.driver_id_code, COALESCE(d.name, u.name) as name,
                       COALESCE(d.phone, u.phone) as phone, d.vehicle_number
                FROM drivers d
                LEFT JOIN users u ON d.user_id = u.id
                ORDER BY d.id DESC LIMIT 20
            ''')
        drivers = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return jsonify({"success": True, "drivers": drivers})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@admin_bp.route('/register_driver', methods=['POST'])
@admin_bp.route('/drivers/create', methods=['POST'])
@admin_required
def register_admin_driver():
    try:
        from werkzeug.security import generate_password_hash
        from database import get_db_connection, generate_unique_driver_id
        import re

        data = request.json or request.form
        username = (data.get('username') or '').strip()
        password = (data.get('password') or '').strip()
        name = (data.get('name') or data.get('full_name') or '').strip()
        phone = (data.get('phone') or data.get('mobile') or '').strip()
        email = (data.get('email') or '').strip()
        dob = (data.get('dob') or '').strip()
        gender = data.get('gender', 'Male')
        address = (data.get('address') or '').strip()
        city = (data.get('city') or 'Erode').strip()
        district = (data.get('district') or 'Erode').strip()
        state = (data.get('state') or 'Tamil Nadu').strip()
        pincode = (data.get('pincode') or '').strip()

        licence_number = (data.get('licence_number') or data.get('driving_license') or '').strip()
        licence_expiry = (data.get('licence_expiry') or '').strip()
        vehicle_number = (data.get('vehicle_number') or '').strip()
        vehicle_type = (data.get('vehicle_type') or 'Car').strip()
        experience = data.get('experience', 0)
        try: experience = int(experience)
        except Exception: experience = 0
        organization = (data.get('organization') or '').strip()
        emergency_contact = (data.get('emergency_contact') or '').strip()

        blood_group = data.get('blood_group', 'O+')
        medical_conditions = (data.get('medical_conditions') or data.get('medical_history') or '').strip()
        medications = (data.get('medications') or '').strip()
        allergies = (data.get('allergies') or '').strip()
        cardiac_history = (data.get('cardiac_history') or '').strip()
        emergency_notes = (data.get('emergency_notes') or '').strip()
        preferred_language = data.get('preferred_language', 'en-US')

        if not username or not password or not name or not phone or not licence_number or not vehicle_number:
            return jsonify({"error": "Full Name, Phone Number, Licence Number, Vehicle Number, Username, and Password are required."}), 400

        clean_phone = re.sub(r'[^\d+]', '', str(phone))
        if len(re.sub(r'\D', '', clean_phone)) < 10:
            return jsonify({"error": "Please enter a valid 10-digit mobile number."}), 400

        if email and '@' not in email:
            return jsonify({"error": "Please enter a valid email address."}), 400

        conn = get_db_connection()
        cursor = conn.cursor()

        # 1. Validate Username Uniqueness
        cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
        if cursor.fetchone():
            conn.close()
            return jsonify({"error": f"Username '{username}' already exists. Please choose a different username."}), 400

        # 2. Validate Licence Number Uniqueness
        if licence_number:
            cursor.execute("SELECT id FROM drivers WHERE licence_number = ? OR driving_license = ?", (licence_number, licence_number))
            if cursor.fetchone():
                conn.close()
                return jsonify({"error": f"Driving Licence Number '{licence_number}' is already registered."}), 400

        # 3. Validate Vehicle Number Uniqueness
        if vehicle_number:
            cursor.execute("SELECT id FROM drivers WHERE vehicle_number = ?", (vehicle_number,))
            if cursor.fetchone():
                conn.close()
                return jsonify({"error": f"Vehicle Number '{vehicle_number}' is already registered to another driver."}), 400

        driver_code = generate_unique_driver_id(conn)
        hashed_pw = generate_password_hash(password, method='pbkdf2:sha256')

        cursor.execute('''
            INSERT INTO users (username, password, role, name, phone, email, verified, is_active, status)
            VALUES (?, ?, 'driver', ?, ?, ?, 1, 1, 'ACTIVE')
        ''', (username, hashed_pw, name, phone, email))
        user_id = cursor.lastrowid

        cursor.execute('''
            INSERT INTO drivers (
                user_id, driver_id_code, name, phone, email, dob, gender, address, city, district, state, pincode,
                licence_number, driving_license, licence_expiry, vehicle_number, vehicle_type, experience, organization,
                emergency_contact, blood_group, medical_conditions, medical_history, medications, allergies,
                cardiac_history, emergency_notes, preferred_language, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'ACTIVE')
        ''', (
            user_id, driver_code, name, phone, email, dob, gender, address, city, district, state, pincode,
            licence_number, licence_number, licence_expiry, vehicle_number, vehicle_type, experience, organization,
            emergency_contact, blood_group, medical_conditions, medical_conditions, medications, allergies,
            cardiac_history, emergency_notes, preferred_language
        ))
        driver_id = cursor.lastrowid

        cursor.execute('''
            INSERT INTO audit_logs (user_id, username, action, details)
            VALUES (?, ?, 'ADMIN_DRIVER_REGISTERED', ?)
        ''', (user_id, username, f"Admin registered Driver {name} ({driver_code})"))

        conn.commit()
        conn.close()

        return jsonify({
            "success": True,
            "message": f"Driver '{name}' registered successfully with ID {driver_code}.",
            "driver_id": driver_id,
            "driver_id_code": driver_code,
            "user_type": "Driver",
            "username": username,
            "status": "ACTIVE"
        }), 201
    except Exception as e:
        print("Error registering driver:", str(e))
        return jsonify({"error": str(e)}), 500


@admin_bp.route('/register_family', methods=['POST'])
@admin_bp.route('/families/create', methods=['POST'])
@admin_required
def register_admin_family():
    try:
        from werkzeug.security import generate_password_hash
        from database import get_db_connection, generate_unique_family_id, verify_driver_id_exists
        import re

        data = request.json or request.form
        username = (data.get('username') or '').strip()
        password = (data.get('password') or '').strip()
        name = (data.get('name') or data.get('full_name') or '').strip()
        relation = (data.get('relation') or data.get('relationship') or 'Family').strip()
        dob = (data.get('dob') or '').strip()
        gender = data.get('gender', 'Female')
        phone = (data.get('phone') or data.get('mobile') or '').strip()
        email = (data.get('email') or '').strip()
        address = (data.get('address') or '').strip()
        city = (data.get('city') or 'Erode').strip()
        district = (data.get('district') or 'Erode').strip()
        state = (data.get('state') or 'Tamil Nadu').strip()
        pincode = (data.get('pincode') or '').strip()
        driver_id_input = (data.get('driver_id') or '').strip()

        primary_emergency_contact = (data.get('primary_emergency_contact') or phone).strip()
        secondary_emergency_contact = (data.get('secondary_emergency_contact') or '').strip()
        notification_preferences = (data.get('notification_preferences') or 'SMS & Voice Call').strip()
        sms_enabled = 1 if str(data.get('sms_enabled', '1')).lower() in ['1', 'true', 'on'] else 0
        alert_enabled = 1 if str(data.get('alert_enabled', '1')).lower() in ['1', 'true', 'on'] else 0

        if not username or not password or not name or not phone or not driver_id_input or not relation:
            return jsonify({"error": "Full Name, Relationship, Phone Number, Linked Driver, Username, and Password are required."}), 400

        clean_phone = re.sub(r'[^\d+]', '', str(phone))
        if len(re.sub(r'\D', '', clean_phone)) < 10:
            return jsonify({"error": "Please enter a valid 10-digit mobile number."}), 400

        if email and '@' not in email:
            return jsonify({"error": "Please enter a valid email address."}), 400

        conn = get_db_connection()
        cursor = conn.cursor()

        # 1. Validate Username Uniqueness
        cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
        if cursor.fetchone():
            conn.close()
            return jsonify({"error": f"Username '{username}' already exists."}), 400

        # 2. Validate Driver Existence & Linking
        driver_info = verify_driver_id_exists(driver_id_input)
        if not driver_info:
            # Fallback search by driver_id_code, name, or phone
            cursor.execute('''
                SELECT d.id, d.driver_id_code, COALESCE(d.name, u.name) as name
                FROM drivers d LEFT JOIN users u ON d.user_id = u.id
                WHERE d.driver_id_code = ? OR d.name LIKE ? OR u.name LIKE ? OR d.phone = ? OR u.phone = ?
            ''', (driver_id_input, f"%{driver_id_input}%", f"%{driver_id_input}%", driver_id_input, driver_id_input))
            row = cursor.fetchone()
            if row:
                driver_info = dict(row)

        if not driver_info:
            conn.close()
            return jsonify({"error": f"Driver with ID / Name '{driver_id_input}' not found. A valid existing Driver must be selected."}), 400

        driver_db_id = driver_info['id']
        canonical_driver_code = driver_info['driver_id_code']
        driver_name = driver_info['name']

        family_code = generate_unique_family_id(conn)
        hashed_pw = generate_password_hash(password, method='pbkdf2:sha256')

        cursor.execute('''
            INSERT INTO users (username, password, role, name, phone, email, verified, is_active, status)
            VALUES (?, ?, 'family', ?, ?, ?, 1, 1, 'ACTIVE')
        ''', (username, hashed_pw, name, phone, email))
        user_id = cursor.lastrowid

        cursor.execute('''
            INSERT INTO family_members (
                user_id, driver_id, family_id_code, name, phone, email, relation, driver_id_code, status,
                dob, gender, address, city, district, state, pincode,
                primary_emergency_contact, secondary_emergency_contact, notification_preferences,
                emergency_sms_consent, emergency_status_consent, notification_enabled, phone_verified, consent_timestamp
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'ACTIVE', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, 1, CURRENT_TIMESTAMP)
        ''', (
            user_id, driver_db_id, family_code, name, phone, email, relation, canonical_driver_code,
            dob, gender, address, city, district, state, pincode,
            primary_emergency_contact, secondary_emergency_contact, notification_preferences,
            sms_enabled, alert_enabled
        ))
        family_id = cursor.lastrowid

        cursor.execute('''
            INSERT INTO audit_logs (user_id, username, action, details)
            VALUES (?, ?, 'ADMIN_FAMILY_REGISTERED', ?)
        ''', (user_id, username, f"Admin registered Family member {name} ({family_code}) linked to Driver {driver_name} ({canonical_driver_code})"))

        conn.commit()
        conn.close()

        return jsonify({
            "success": True,
            "message": f"Family Member '{name}' registered successfully with ID {family_code} linked to Driver {driver_name} ({canonical_driver_code}).",
            "family_id": family_id,
            "family_id_code": family_code,
            "linked_driver": f"{canonical_driver_code} - {driver_name}",
            "user_type": "Family Member",
            "username": username,
            "status": "ACTIVE"
        }), 201
    except Exception as e:
        print("Error registering family member:", str(e))
        return jsonify({"error": str(e)}), 500


@admin_bp.route('/register_ambulance', methods=['POST'])
@admin_bp.route('/ambulances/create', methods=['POST'])
@admin_required
def register_admin_ambulance():
    try:
        from werkzeug.security import generate_password_hash
        from database import get_db_connection, generate_unique_ambulance_id
        from geocoding_service import geocode_address_fallback, DEFAULT_LAT, DEFAULT_LNG
        import json, re

        data = request.json or request.form
        username = (data.get('username') or '').strip()
        password = (data.get('password') or '').strip()
        name = (data.get('name') or data.get('full_name') or '').strip()
        phone = (data.get('phone') or data.get('mobile') or '').strip()
        email = (data.get('email') or '').strip()
        dob = (data.get('dob') or '').strip()
        gender = data.get('gender', 'Male')
        address = (data.get('address') or 'Erode, Tamil Nadu').strip()
        city = (data.get('city') or 'Erode').strip()
        district = (data.get('district') or 'Erode').strip()
        state = (data.get('state') or 'Tamil Nadu').strip()
        pincode = (data.get('pincode') or '').strip()

        licence_number = (data.get('licence_number') or '').strip()
        licence_expiry = (data.get('licence_expiry') or '').strip()
        experience = data.get('experience', 0)
        try: experience = int(experience)
        except Exception: experience = 0

        vehicle_number = (data.get('vehicle_number') or data.get('ambulance_registration_number') or '').strip()
        ambulance_type = (data.get('ambulance_type') or 'Basic Life Support (BLS)').strip()
        service_provider = (data.get('service_provider') or '').strip()
        organization = (data.get('organization') or data.get('hospital_name') or '').strip()
        organization_address = (data.get('organization_address') or '').strip()
        emergency_contact = (data.get('emergency_contact') or phone).strip()

        raw_capabilities = data.get('capabilities', ['Basic Life Support (BLS)'])
        if isinstance(raw_capabilities, list):
            capabilities_str = json.dumps(raw_capabilities)
        else:
            capabilities_str = str(raw_capabilities)

        availability = (data.get('availability') or data.get('status') or 'AVAILABLE').upper()
        if availability not in ['AVAILABLE', 'BUSY', 'OFFLINE']:
            availability = 'AVAILABLE'

        preferred_language = data.get('preferred_language', 'en')
        hospital_id = data.get('hospital_id')
        hospital_id = int(hospital_id) if hospital_id and str(hospital_id).isdigit() else None

        if not username or not password or not name or not phone or not licence_number or not vehicle_number:
            return jsonify({"error": "Driver Full Name, Phone Number, Driving Licence, Vehicle Registration Number, Username, and Password are required."}), 400

        clean_phone = re.sub(r'[^\d+]', '', str(phone))
        if len(re.sub(r'\D', '', clean_phone)) < 10:
            return jsonify({"error": "Please enter a valid 10-digit phone number."}), 400

        conn = get_db_connection()
        cursor = conn.cursor()

        # 1. Validate Username Uniqueness
        cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
        if cursor.fetchone():
            conn.close()
            return jsonify({"error": f"Username '{username}' already exists."}), 400

        # 2. Validate Driving Licence Uniqueness
        if licence_number:
            cursor.execute("SELECT id FROM ambulances WHERE licence_number = ?", (licence_number,))
            if cursor.fetchone():
                conn.close()
                return jsonify({"error": f"Driving Licence '{licence_number}' is already registered to another ambulance driver."}), 400

        # 3. Validate Vehicle Number Uniqueness
        if vehicle_number:
            cursor.execute("SELECT id FROM ambulances WHERE vehicle_number = ? OR ambulance_registration_number = ?", (vehicle_number, vehicle_number))
            if cursor.fetchone():
                conn.close()
                return jsonify({"error": f"Ambulance Registration Number '{vehicle_number}' is already registered."}), 400

        hashed_pw = generate_password_hash(password, method='pbkdf2:sha256')

        cursor.execute('''
            INSERT INTO users (username, password, role, name, phone, email, hospital_id, verified, is_active, status)
            VALUES (?, ?, 'ambulance', ?, ?, ?, ?, 1, 1, ?)
        ''', (username, hashed_pw, name, phone, email, hospital_id, availability))
        user_id = cursor.lastrowid

        hosp_code = None
        if hospital_id:
            cursor.execute("SELECT hospital_id_code FROM hospitals WHERE id = ?", (hospital_id,))
            h_row = cursor.fetchone()
            if h_row:
                hosp_code = h_row['hospital_id_code']

        amb_code = generate_unique_ambulance_id(
            is_private=(not hospital_id),
            hospital_id_code=hosp_code,
            city=address,
            conn=conn,
            prefix="AMB-"
        )
        final_vehicle_no = vehicle_number if vehicle_number else amb_code

        lat, lng = DEFAULT_LAT, DEFAULT_LNG
        geo_res = geocode_address_fallback(f"{address}, {city}, {district}, {state}")
        if geo_res:
            lat, lng = geo_res

        cursor.execute('''
            INSERT INTO ambulances (
                hospital_id, vehicle_number, ambulance_registration_number, driver_name, driver_phone, status,
                driver_user_id, emergency_call_consent, emergency_call_enabled, preferred_language, phone_verified,
                consent_timestamp, latitude, longitude, ambulance_driver_id_code, dob, gender, address, city,
                district, state, pincode, licence_number, licence_expiry, experience, service_provider,
                organization, organization_address, emergency_contact, capabilities, current_location, last_location_update
            ) VALUES (?, ?, ?, ?, ?, ?, ?, 1, 1, ?, 1, CURRENT_TIMESTAMP, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ''', (
            hospital_id, final_vehicle_no, final_vehicle_no, name, phone, availability,
            user_id, preferred_language, lat, lng, amb_code, dob, gender, address, city,
            district, state, pincode, licence_number, licence_expiry, experience, service_provider,
            organization, organization_address, emergency_contact, capabilities_str, f"{city}, {state}"
        ))
        amb_id = cursor.lastrowid

        cursor.execute('''
            INSERT INTO audit_logs (user_id, username, action, details)
            VALUES (?, ?, 'ADMIN_AMBULANCE_REGISTERED', ?)
        ''', (user_id, username, f"Admin registered Private Ambulance Driver {name} ({amb_code})"))

        conn.commit()
        conn.close()

        return jsonify({
            "success": True,
            "message": f"Private Ambulance Driver '{name}' registered successfully with ID {amb_code}.",
            "ambulance_id": amb_id,
            "ambulance_driver_id_code": amb_code,
            "vehicle_number": final_vehicle_no,
            "user_type": "Private Ambulance Driver",
            "username": username,
            "status": availability
        }), 201
    except Exception as e:
        print("Error registering ambulance driver:", str(e))
        return jsonify({"error": str(e)}), 500




@admin_bp.route('/hospitals/<int:hospital_id>/edit', methods=['POST'])
@admin_required
def edit_hospital(hospital_id):
    try:
        from database import get_db_connection
        from geocoding_service import geocode_address_fallback
        import re

        data = request.json or request.form
        name = data.get('name')
        hospital_type = data.get('hospital_type') or 'Multi-Speciality'
        phone = data.get('phone')
        email = data.get('email', '')
        address = data.get('address')
        city = data.get('city') or 'Erode'
        district = data.get('district') or 'Erode'
        state = data.get('state') or 'Tamil Nadu'
        pincode = data.get('pincode', '')
        status = data.get('status', 'ACTIVE').upper()

        if not name or not phone or not address:
            return jsonify({"error": "Hospital Name, Phone, and Address are required."}), 400

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM hospitals WHERE id = ?", (hospital_id,))
        existing_row = cursor.fetchone()
        if not existing_row:
            conn.close()
            return jsonify({"error": "Hospital not found"}), 404
        existing = dict(existing_row)

        # Check if address changed -> re-geocode if needed
        final_lat = existing['latitude']
        final_lng = existing['longitude']
        if address != existing['address']:
            full_addr = f"{address}, {city}, {district}, {state}, India"
            geo_res = geocode_address_fallback(full_addr)
            if geo_res:
                final_lat, final_lng = geo_res

        cursor.execute('''
            UPDATE hospitals SET
                name = ?, hospital_type = ?, emergency_number = ?, email = ?, address = ?,
                city = ?, district = ?, state = ?, pincode = ?, latitude = ?, longitude = ?,
                emergency_available = ?, icu_availability = ?, cardiology_availability = ?, neurology_availability = ?,
                available_beds = ?, icu_beds = ?, ambulance_availability = ?, status = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (
            name, hospital_type, phone, email, address,
            city, district, state, pincode, final_lat, final_lng,
            1 if data.get('emergency_available', True) else 0,
            1 if data.get('icu_available', True) else 0,
            1 if data.get('cardiology_available', True) else 0,
            1 if data.get('neurology_available', True) else 0,
            int(data.get('available_beds', 10)),
            int(data.get('icu_beds', 5)),
            1 if data.get('ambulance_available', True) else 0,
            status, hospital_id
        ))

        # Check for password update
        password = data.get('password')
        if password and str(password).strip() and existing.get('user_id'):
            from werkzeug.security import generate_password_hash
            hashed_pw = generate_password_hash(str(password).strip(), method='pbkdf2:sha256')
            cursor.execute("UPDATE users SET password = ? WHERE id = ?", (hashed_pw, existing['user_id']))

        conn.commit()
        conn.close()
        return jsonify({"success": True, "message": f"Hospital '{name}' updated successfully."})
    except Exception as e:
        print("Error editing hospital:", str(e))
        return jsonify({"error": str(e)}), 500


@admin_bp.route('/hospitals/<int:hospital_id>/toggle-status', methods=['POST'])
@admin_required
def toggle_hospital_status(hospital_id):
    try:
        from database import get_db_connection
        data = request.json or {}
        new_status = data.get('status', '').upper()

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT status, name FROM hospitals WHERE id = ?", (hospital_id,))
        row = cursor.fetchone()
        if not row:
            conn.close()
            return jsonify({"error": "Hospital not found"}), 404

        if not new_status:
            new_status = 'INACTIVE' if row['status'] == 'ACTIVE' else 'ACTIVE'

        cursor.execute("UPDATE hospitals SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?", (new_status, hospital_id))
        conn.commit()
        conn.close()
        return jsonify({"success": True, "message": f"Hospital '{row['name']}' status set to {new_status}."})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@admin_bp.route('/api/admin/hospitals/verify', methods=['POST'])
@admin_required
def verify_hospital_data():
    """Verify hospital specialty, service, or emergency status."""
    try:
        from database import get_db_connection
        data = request.json
        hospital_id = data.get('hospital_id')
        specialty = data.get('specialty')
        service = data.get('service')
        emergency_available = data.get('emergency_available')

        if not hospital_id:
            return jsonify({"error": "hospital_id is required"}), 400

        conn = get_db_connection()
        cursor = conn.cursor()

        if specialty:
            cursor.execute("SELECT id FROM hospital_specialties WHERE hospital_id = ? AND specialty = ?", (hospital_id, specialty))
            if not cursor.fetchone():
                cursor.execute("INSERT INTO hospital_specialties (hospital_id, specialty, verified, source) VALUES (?, ?, 1, 'Admin Verified')", (hospital_id, specialty))
            else:
                cursor.execute("UPDATE hospital_specialties SET verified = 1, source = 'Admin Verified' WHERE hospital_id = ? AND specialty = ?", (hospital_id, specialty))

        if service:
            cursor.execute("SELECT id FROM hospital_services WHERE hospital_id = ? AND service_name = ?", (hospital_id, service))
            if not cursor.fetchone():
                cursor.execute("INSERT INTO hospital_services (hospital_id, service_name, verified, source) VALUES (?, ?, 1, 'Admin Verified')", (hospital_id, service))
            else:
                cursor.execute("UPDATE hospital_services SET verified = 1, source = 'Admin Verified' WHERE hospital_id = ? AND service_name = ?", (hospital_id, service))

        if emergency_available is not None:
            cursor.execute("UPDATE hospitals SET emergency_available = ?, verified = 1, source = 'Admin Verified' WHERE id = ?", (1 if emergency_available else 0, hospital_id))

        conn.commit()
        conn.close()
        return jsonify({"success": True, "message": "Hospital data verified successfully."})
    except Exception as e:
        print("Error verifying hospital data:", str(e))
        return jsonify({"error": "Failed to verify hospital data"}), 500


@admin_bp.route('/api/admin/doctors/add', methods=['POST'])
@admin_required
def add_admin_doctor():
    """Add or update verified doctor profile for a hospital."""
    try:
        from database import get_db_connection
        data = request.json
        hospital_id = data.get('hospital_id')
        name = data.get('name')
        specialty = data.get('specialty')
        qualification = data.get('qualification', '')
        experience = data.get('experience', '')
        working_days = data.get('working_days', 'Mon - Sat')
        working_hours = data.get('working_hours', '10:00 AM - 04:00 PM')
        contact_info = data.get('contact_info', '')

        if not hospital_id or not name or not specialty:
            return jsonify({"error": "hospital_id, name, and specialty are required"}), 400

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO doctors (hospital_id, name, specialty, qualification, experience, availability, working_days, working_hours, contact_info, verified, source)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1, 'Admin Verified')
        ''', (hospital_id, name, specialty, qualification, experience, working_days, working_days, working_hours, contact_info))

        conn.commit()
        conn.close()
        return jsonify({"success": True, "message": f"Doctor {name} added and verified successfully."})
    except Exception as e:
        print("Error adding doctor:", str(e))
        return jsonify({"error": "Failed to add doctor profile"}), 500



@admin_bp.route('/drivers', methods=['GET'])
@admin_required
def get_admin_drivers():
    try:
        from database import get_db_connection
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT d.id, d.driver_id_code, COALESCE(d.name, u.name) as name,
                   COALESCE(d.phone, u.phone) as phone, COALESCE(d.email, u.email) as email,
                   d.age, d.gender, d.blood_group, d.preferred_language,
                   u.username, COALESCE(u.is_active, 1) as is_active,
                   COALESCE(d.status, 'ACTIVE') as status, u.created_at
            FROM drivers d
            LEFT JOIN users u ON d.user_id = u.id
            ORDER BY d.id DESC
        ''')
        drivers = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return jsonify({"success": True, "drivers": drivers})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@admin_bp.route('/families', methods=['GET'])
@admin_required
def get_admin_families():
    try:
        from database import get_db_connection
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT f.id, f.family_id_code, COALESCE(f.name, u.name) as family_name, f.relation,
                   f.driver_id_code, d.id as driver_id, COALESCE(d.name, du.name) as driver_name,
                   COALESCE(f.phone, u.phone) as phone, COALESCE(f.email, u.email) as email,
                   u.username, COALESCE(u.is_active, 1) as is_active,
                   COALESCE(f.status, 'ACTIVE') as status, f.created_at
            FROM family_members f
            LEFT JOIN users u ON f.user_id = u.id
            LEFT JOIN drivers d ON f.driver_id = d.id
            LEFT JOIN users du ON d.user_id = du.id
            ORDER BY f.id DESC
        ''')
        families = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return jsonify({"success": True, "families": families})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@admin_bp.route('/ambulances', methods=['GET'])
@admin_required
def get_admin_ambulances():
    try:
        from database import get_db_connection
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT a.id,
                   ('AMB-' || printf('%06d', a.id)) as ambulance_driver_id_code,
                   a.driver_name, a.driver_phone as phone, u.email, a.vehicle_number,
                   h.name as hospital_name, u.username, COALESCE(u.is_active, 1) as is_active,
                   UPPER(COALESCE(a.status, 'Available')) as status,
                   a.phone_verified, a.consent_timestamp as created_at
            FROM ambulances a
            LEFT JOIN users u ON (a.driver_user_id = u.id OR a.user_id = u.id)
            LEFT JOIN hospitals h ON a.hospital_id = h.id
            ORDER BY a.id DESC
        ''')
        ambulances = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return jsonify({"success": True, "ambulances": ambulances})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@admin_bp.route('/staff', methods=['GET'])
@admin_required
def get_admin_staff():
    try:
        from database import get_db_connection
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Combine hospital_staff with doctors, nurses, receptionists, pharmacists, ambulance_drivers
        cursor.execute('''
            SELECT u.id as user_id,
                   COALESCE(s.id, doc.id, nur.id, rec.id, pha.id, amb.id) as id,
                   COALESCE(s.staff_id_code, doc.doctor_id_code, nur.nurse_id_code, rec.receptionist_id_code, pha.pharmacist_id_code, amb.driver_id_code, 'STA-000001') as staff_id_code,
                   COALESCE(u.name, s.name, doc.name, nur.name, rec.name, pha.name, amb.name) as name,
                   COALESCE(s.sub_role, u.role, 'Staff') as staff_role,
                   COALESCE(u.phone, s.phone, doc.phone, nur.phone, rec.phone, pha.phone, amb.phone) as phone,
                   COALESCE(u.email, s.email, doc.email, nur.email, rec.email, pha.email, amb.email) as email,
                   h.name as hospital_name, u.username, COALESCE(u.is_active, 1) as is_active,
                   CASE WHEN COALESCE(u.is_active, 1) = 1 THEN 'ACTIVE' ELSE 'INACTIVE' END as status,
                   u.created_at
            FROM users u
            LEFT JOIN hospitals h ON u.hospital_id = h.id
            LEFT JOIN hospital_staff s ON s.user_id = u.id
            LEFT JOIN doctors doc ON doc.user_id = u.id
            LEFT JOIN nurses nur ON nur.user_id = u.id
            LEFT JOIN receptionists rec ON rec.user_id = u.id
            LEFT JOIN pharmacists pha ON pha.user_id = u.id
            LEFT JOIN ambulance_drivers amb ON amb.user_id = u.id
            WHERE u.role IN ('doctor', 'nurse', 'receptionist', 'pharmacist', 'hospital_staff', 'ambulance_driver')
               OR s.id IS NOT NULL OR doc.id IS NOT NULL OR nur.id IS NOT NULL
            ORDER BY u.id DESC
        ''')

        staff_list = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return jsonify({"success": True, "staff": staff_list})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@admin_bp.route('/entity/toggle-active', methods=['POST'])
@admin_required
def toggle_admin_entity():
    try:
        from database import get_db_connection
        data = request.json or {}
        entity_type = data.get('entity_type')
        entity_id = data.get('entity_id')

        if not entity_type or not entity_id:
            return jsonify({"error": "entity_type and entity_id required"}), 400

        conn = get_db_connection()
        cursor = conn.cursor()
        new_status = 'ACTIVE'

        if entity_type == 'driver':
            cursor.execute("SELECT status, user_id FROM drivers WHERE id = ?", (entity_id,))
            row = cursor.fetchone()
            if row:
                curr = (row['status'] or 'ACTIVE').upper()
                new_status = 'INACTIVE' if curr == 'ACTIVE' else 'ACTIVE'
                new_active = 1 if new_status == 'ACTIVE' else 0
                cursor.execute("UPDATE drivers SET status = ? WHERE id = ?", (new_status, entity_id))
                if row['user_id']:
                    cursor.execute("UPDATE users SET is_active = ?, status = ? WHERE id = ?", (new_active, new_status, row['user_id']))

        elif entity_type == 'family':
            cursor.execute("SELECT status, user_id FROM family_members WHERE id = ?", (entity_id,))
            row = cursor.fetchone()
            if row:
                curr = (row['status'] or 'ACTIVE').upper()
                new_status = 'INACTIVE' if curr == 'ACTIVE' else 'ACTIVE'
                new_active = 1 if new_status == 'ACTIVE' else 0
                cursor.execute("UPDATE family_members SET status = ? WHERE id = ?", (new_status, entity_id))
                if row['user_id']:
                    cursor.execute("UPDATE users SET is_active = ?, status = ? WHERE id = ?", (new_active, new_status, row['user_id']))

        elif entity_type == 'ambulance':
            cursor.execute("SELECT status, driver_user_id, user_id FROM ambulances WHERE id = ?", (entity_id,))
            row = cursor.fetchone()
            if row:
                curr = (row['status'] or 'AVAILABLE').upper()
                new_status = 'INACTIVE' if curr in ['AVAILABLE', 'BUSY'] else 'AVAILABLE'
                new_active = 1 if new_status == 'AVAILABLE' else 0
                cursor.execute("UPDATE ambulances SET status = ? WHERE id = ?", (new_status, entity_id))
                u_id = row['driver_user_id'] or row['user_id']
                if u_id:
                    cursor.execute("UPDATE users SET is_active = ?, status = ? WHERE id = ?", (new_active, new_status, u_id))

        elif entity_type == 'hospital':
            cursor.execute("SELECT status, admin_user_id FROM hospitals WHERE id = ?", (entity_id,))
            row = cursor.fetchone()
            if row:
                curr = (row['status'] or 'ACTIVE').upper()
                new_status = 'INACTIVE' if curr == 'ACTIVE' else 'ACTIVE'
                new_active = 1 if new_status == 'ACTIVE' else 0
                cursor.execute("UPDATE hospitals SET status = ? WHERE id = ?", (new_status, entity_id))
                if row['admin_user_id']:
                    cursor.execute("UPDATE users SET is_active = ?, status = ? WHERE id = ?", (new_active, new_status, row['admin_user_id']))

        elif entity_type in ['staff', 'doctor', 'nurse', 'receptionist', 'pharmacist']:
            cursor.execute("SELECT is_active FROM users WHERE id = ?", (entity_id,))
            row = cursor.fetchone()
            if not row:
                cursor.execute("SELECT user_id FROM hospital_staff WHERE id = ?", (entity_id,))
                row = cursor.fetchone()
            
            u_id = row['user_id'] if row and 'user_id' in row.keys() else entity_id
            cursor.execute("SELECT is_active FROM users WHERE id = ?", (u_id,))
            ur = cursor.fetchone()
            curr_active = ur['is_active'] if ur and ur['is_active'] is not None else 1
            new_active = 0 if curr_active == 1 else 1
            new_status = 'ACTIVE' if new_active == 1 else 'INACTIVE'
            
            cursor.execute("UPDATE users SET is_active = ?, status = ? WHERE id = ?", (new_active, new_status, u_id))
            cursor.execute("UPDATE hospital_staff SET status = ? WHERE user_id = ? OR id = ?", (new_status, u_id, entity_id))

        conn.commit()
        conn.close()
        return jsonify({"success": True, "new_status": new_status, "message": f"Status updated to {new_status}."})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@admin_bp.route('/entity/edit', methods=['POST'])
@admin_required
def edit_admin_entity():
    try:
        from database import get_db_connection
        from werkzeug.security import generate_password_hash
        data = request.json or {}
        entity_type = data.get('entity_type')
        entity_id = data.get('entity_id')

        if not entity_type or not entity_id:
            return jsonify({"error": "entity_type and entity_id required"}), 400

        conn = get_db_connection()
        cursor = conn.cursor()

        name = data.get('name')
        phone = data.get('phone')
        email = data.get('email')
        username = data.get('username')
        password = data.get('password')
        status = data.get('status', 'ACTIVE')

        if entity_type == 'driver':
            cursor.execute("SELECT user_id FROM drivers WHERE id = ?", (entity_id,))
            r = cursor.fetchone()
            cursor.execute("""
                UPDATE drivers 
                SET name = COALESCE(?, name),
                    phone = COALESCE(?, phone),
                    email = COALESCE(?, email),
                    status = COALESCE(?, status)
                WHERE id = ?
            """, (name, phone, email, status, entity_id))
            if r and r['user_id']:
                u_id = r['user_id']
                cursor.execute("""
                    UPDATE users
                    SET name = COALESCE(?, name),
                        phone = COALESCE(?, phone),
                        email = COALESCE(?, email),
                        username = COALESCE(?, username),
                        status = COALESCE(?, status)
                    WHERE id = ?
                """, (name, phone, email, username, status, u_id))
                if password and password.strip():
                    hashed = generate_password_hash(password.strip(), method='pbkdf2:sha256')
                    cursor.execute("UPDATE users SET password = ? WHERE id = ?", (hashed, u_id))

        elif entity_type == 'family':
            cursor.execute("SELECT user_id FROM family_members WHERE id = ?", (entity_id,))
            r = cursor.fetchone()
            cursor.execute("""
                UPDATE family_members 
                SET name = COALESCE(?, name),
                    phone = COALESCE(?, phone),
                    email = COALESCE(?, email),
                    status = COALESCE(?, status)
                WHERE id = ?
            """, (name, phone, email, status, entity_id))
            if r and r['user_id']:
                u_id = r['user_id']
                cursor.execute("""
                    UPDATE users
                    SET name = COALESCE(?, name),
                        phone = COALESCE(?, phone),
                        email = COALESCE(?, email),
                        username = COALESCE(?, username),
                        status = COALESCE(?, status)
                    WHERE id = ?
                """, (name, phone, email, username, status, u_id))
                if password and password.strip():
                    hashed = generate_password_hash(password.strip(), method='pbkdf2:sha256')
                    cursor.execute("UPDATE users SET password = ? WHERE id = ?", (hashed, u_id))

        elif entity_type == 'ambulance':
            cursor.execute("SELECT driver_user_id, user_id FROM ambulances WHERE id = ?", (entity_id,))
            r = cursor.fetchone()
            cursor.execute("""
                UPDATE ambulances 
                SET driver_name = COALESCE(?, driver_name),
                    driver_phone = COALESCE(?, driver_phone),
                    vehicle_number = COALESCE(?, vehicle_number),
                    status = COALESCE(?, status)
                WHERE id = ?
            """, (name, phone, data.get('vehicle_number'), status, entity_id))
            u_id = r['driver_user_id'] if r and r['driver_user_id'] else (r['user_id'] if r else None)
            if u_id:
                cursor.execute("""
                    UPDATE users
                    SET name = COALESCE(?, name),
                        phone = COALESCE(?, phone),
                        email = COALESCE(?, email),
                        username = COALESCE(?, username),
                        status = COALESCE(?, status)
                    WHERE id = ?
                """, (name, phone, email, username, status, u_id))
                if password and password.strip():
                    hashed = generate_password_hash(password.strip(), method='pbkdf2:sha256')
                    cursor.execute("UPDATE users SET password = ? WHERE id = ?", (hashed, u_id))

        elif entity_type == 'hospital':
            cursor.execute("SELECT admin_user_id FROM hospitals WHERE id = ?", (entity_id,))
            r = cursor.fetchone()
            cursor.execute("""
                UPDATE hospitals 
                SET name = COALESCE(?, name),
                    phone = COALESCE(?, phone),
                    email = COALESCE(?, email),
                    status = COALESCE(?, status)
                WHERE id = ?
            """, (name, phone, email, status, entity_id))
            if r and r['admin_user_id']:
                u_id = r['admin_user_id']
                cursor.execute("""
                    UPDATE users
                    SET name = COALESCE(?, name),
                        phone = COALESCE(?, phone),
                        email = COALESCE(?, email),
                        username = COALESCE(?, username),
                        status = COALESCE(?, status)
                    WHERE id = ?
                """, (name, phone, email, username, status, u_id))
                if password and password.strip():
                    hashed = generate_password_hash(password.strip(), method='pbkdf2:sha256')
                    cursor.execute("UPDATE users SET password = ? WHERE id = ?", (hashed, u_id))

        elif entity_type in ['staff', 'doctor', 'nurse', 'receptionist', 'pharmacist']:
            cursor.execute("SELECT user_id FROM hospital_staff WHERE id = ? OR user_id = ?", (entity_id, entity_id))
            r = cursor.fetchone()
            u_id = r['user_id'] if r else entity_id
            cursor.execute("""
                UPDATE hospital_staff 
                SET name = COALESCE(?, name),
                    phone = COALESCE(?, phone),
                    email = COALESCE(?, email),
                    status = COALESCE(?, status)
                WHERE id = ? OR user_id = ?
            """, (name, phone, email, status, entity_id, u_id))
            if u_id:
                cursor.execute("""
                    UPDATE users
                    SET name = COALESCE(?, name),
                        phone = COALESCE(?, phone),
                        email = COALESCE(?, email),
                        username = COALESCE(?, username),
                        status = COALESCE(?, status)
                    WHERE id = ?
                """, (name, phone, email, username, status, u_id))
                if password and password.strip():
                    hashed = generate_password_hash(password.strip(), method='pbkdf2:sha256')
                    cursor.execute("UPDATE users SET password = ? WHERE id = ?", (hashed, u_id))

        conn.commit()
        conn.close()
        return jsonify({"success": True, "message": f"{entity_type.capitalize()} updated successfully."})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@admin_bp.route('/entity/delete', methods=['POST'])
@admin_required
def delete_admin_entity():
    try:
        from database import get_db_connection
        data = request.json or {}
        entity_type = data.get('entity_type')
        entity_id = data.get('entity_id')
        force = data.get('force', False)

        if not entity_type or not entity_id:
            return jsonify({"error": "entity_type and entity_id required"}), 400

        conn = get_db_connection()
        cursor = conn.cursor()

        if entity_type == 'driver':
            cursor.execute("SELECT COUNT(*) FROM family_members WHERE driver_id = ?", (entity_id,))
            linked_fam_count = cursor.fetchone()[0]
            if linked_fam_count > 0 and not force:
                conn.close()
                return jsonify({
                    "warning": True,
                    "message": f"This driver has {linked_fam_count} linked family member(s). Deleting will remove these relationships. Proceed?",
                    "linked_family_count": linked_fam_count
                }), 200
            
            cursor.execute("SELECT user_id, phone, name FROM drivers WHERE id = ? OR user_id = ?", (entity_id, entity_id))
            row = cursor.fetchone()
            if row:
                u_id = row['user_id']
                phone = row['phone']
                cursor.execute("DELETE FROM users WHERE id = ? OR (role = 'driver' AND phone = ?)", (u_id, phone))
            cursor.execute("DELETE FROM drivers WHERE id = ? OR user_id = ?", (entity_id, entity_id))
            cursor.execute("UPDATE family_members SET driver_id = NULL WHERE driver_id = ?", (entity_id,))

        elif entity_type == 'family':
            cursor.execute("SELECT user_id, phone FROM family_members WHERE id = ? OR user_id = ?", (entity_id, entity_id))
            row = cursor.fetchone()
            if row:
                cursor.execute("DELETE FROM users WHERE id = ? OR (role = 'family' AND phone = ?)", (row['user_id'], row['phone']))
            cursor.execute("DELETE FROM family_members WHERE id = ? OR user_id = ?", (entity_id, entity_id))

        elif entity_type == 'hospital':
            cursor.execute("SELECT admin_user_id FROM hospitals WHERE id = ?", (entity_id,))
            row = cursor.fetchone()
            if row and row['admin_user_id']:
                cursor.execute("DELETE FROM users WHERE id = ?", (row['admin_user_id'],))
            cursor.execute("DELETE FROM users WHERE hospital_id = ? AND role IN ('hospital', 'hospital_admin')", (entity_id,))
            cursor.execute("DELETE FROM hospitals WHERE id = ?", (entity_id,))

        elif entity_type == 'ambulance':
            cursor.execute("SELECT driver_user_id, user_id FROM ambulances WHERE id = ?", (entity_id,))
            row = cursor.fetchone()
            if row:
                u1 = row['driver_user_id']
                u2 = row['user_id']
                if u1: cursor.execute("DELETE FROM users WHERE id = ?", (u1,))
                if u2: cursor.execute("DELETE FROM users WHERE id = ?", (u2,))
            cursor.execute("DELETE FROM ambulances WHERE id = ?", (entity_id,))

        elif entity_type in ['staff', 'doctor', 'nurse', 'receptionist', 'pharmacist']:
            u_id = None
            code = None
            
            cursor.execute("SELECT user_id, staff_id_code FROM hospital_staff WHERE id = ? OR user_id = ?", (entity_id, entity_id))
            r = cursor.fetchone()
            if r:
                u_id = r['user_id']
                code = r['staff_id_code']
            
            if not u_id:
                cursor.execute("SELECT user_id, doctor_id_code FROM doctors WHERE id = ? OR user_id = ?", (entity_id, entity_id))
                r = cursor.fetchone()
                if r: u_id = r['user_id']; code = r['doctor_id_code']
            if not u_id:
                cursor.execute("SELECT user_id, nurse_id_code FROM nurses WHERE id = ? OR user_id = ?", (entity_id, entity_id))
                r = cursor.fetchone()
                if r: u_id = r['user_id']; code = r['nurse_id_code']
            if not u_id:
                cursor.execute("SELECT user_id, receptionist_id_code FROM receptionists WHERE id = ? OR user_id = ?", (entity_id, entity_id))
                r = cursor.fetchone()
                if r: u_id = r['user_id']; code = r['receptionist_id_code']
            if not u_id:
                cursor.execute("SELECT user_id, pharmacist_id_code FROM pharmacists WHERE id = ? OR user_id = ?", (entity_id, entity_id))
                r = cursor.fetchone()
                if r: u_id = r['user_id']; code = r['pharmacist_id_code']
            if not u_id:
                u_id = entity_id

            # Clean delete across all staff tables & users table
            if u_id:
                cursor.execute("DELETE FROM users WHERE id = ?", (u_id,))
            cursor.execute("DELETE FROM hospital_staff WHERE id = ? OR user_id = ? OR (staff_id_code IS NOT NULL AND staff_id_code = ?)", (entity_id, u_id, code))
            cursor.execute("DELETE FROM doctors WHERE id = ? OR user_id = ? OR (doctor_id_code IS NOT NULL AND doctor_id_code = ?)", (entity_id, u_id, code))
            cursor.execute("DELETE FROM nurses WHERE id = ? OR user_id = ? OR (nurse_id_code IS NOT NULL AND nurse_id_code = ?)", (entity_id, u_id, code))
            cursor.execute("DELETE FROM receptionists WHERE id = ? OR user_id = ? OR (receptionist_id_code IS NOT NULL AND receptionist_id_code = ?)", (entity_id, u_id, code))
            cursor.execute("DELETE FROM pharmacists WHERE id = ? OR user_id = ? OR (pharmacist_id_code IS NOT NULL AND pharmacist_id_code = ?)", (entity_id, u_id, code))
            cursor.execute("DELETE FROM ambulance_drivers WHERE id = ? OR user_id = ?", (entity_id, u_id))

        conn.commit()
        conn.close()
        return jsonify({"success": True, "message": f"{entity_type.capitalize()} deleted successfully."})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
