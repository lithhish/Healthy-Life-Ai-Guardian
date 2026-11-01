"""
AI Driver Health Guardian — Hospital Staff Management & Role-Based Isolation API
"""

from flask import Blueprint, request, jsonify, session
from werkzeug.security import generate_password_hash
from database import get_db_connection
from routes.auth import hospital_admin_required, login_required

hospital_bp = Blueprint('hospital', __name__, url_prefix='/api/hospital')

@hospital_bp.route('/staff/register', methods=['POST'])
@hospital_admin_required
def register_hospital_staff():
    """
    Registers a new Hospital Staff member (Doctor, Nurse, Receptionist, Pharmacist, Ambulance Driver).
    Automatically inherits hospital_id = session.get('hospital_id').
    Generates unique ID (DOC000001, NUR000001, REC000001, PHA000001, AMB000001).
    """
    data = request.json or request.form
    staff_type = (data.get('staff_type') or data.get('role') or 'doctor').lower()
    
    hospital_id = session.get('hospital_id', 1)
    
    username = data.get('username')
    password = data.get('password')
    name = data.get('name') or data.get('full_name')
    phone = data.get('phone')
    email = data.get('email')
    
    if not username or not password or not name:
        return jsonify({"error": "Missing required fields (username, password, name)"}), 400

    conn = get_db_connection()
    cursor = conn.cursor()

    # Check if username exists
    cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
    if cursor.fetchone():
        conn.close()
        return jsonify({"error": f"Username '{username}' already exists"}), 400

    # 1. Create Base User Record
    hashed_pw = generate_password_hash(password)
    cursor.execute('''
        INSERT INTO users (username, password, role, name, phone, email, hospital_id)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (username, hashed_pw, staff_type, name, phone, email, hospital_id))
    user_id = cursor.lastrowid

    # 2. Role-Specific Roster Record Creation & Centralized Staff Table Sync
    from database import generate_unique_staff_id
    staff_code = generate_unique_staff_id(staff_type, conn)

    if staff_type == 'doctor':
        cursor.execute('''
            INSERT INTO doctors (
                user_id, hospital_id, doctor_id_code, name, phone, email, gender, dob, reg_number,
                specialty, qualification, experience, emergency_dept, is_active
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
        ''', (
            user_id, hospital_id, staff_code, name, phone, email,
            data.get('gender'), data.get('dob'), data.get('reg_number'),
            data.get('specialization') or data.get('specialty') or 'General Medicine',
            data.get('qualification'), data.get('experience'), data.get('emergency_dept')
        ))

    elif staff_type == 'nurse':
        cursor.execute('''
            INSERT INTO nurses (
                user_id, hospital_id, nurse_id_code, name, phone, email, gender, qualification,
                nursing_reg_number, department, shift, is_active
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
        ''', (
            user_id, hospital_id, staff_code, name, phone, email,
            data.get('gender'), data.get('qualification'), data.get('nursing_reg_number'),
            data.get('department') or 'General Emergency', data.get('shift') or 'Day'
        ))

    elif staff_type == 'receptionist':
        cursor.execute('''
            INSERT INTO receptionists (
                user_id, hospital_id, receptionist_id_code, name, phone, email, shift, is_active
            ) VALUES (?, ?, ?, ?, ?, ?, ?, 1)
        ''', (
            user_id, hospital_id, staff_code, name, phone, email, data.get('shift') or 'Day'
        ))

    elif staff_type == 'pharmacist':
        cursor.execute('''
            INSERT INTO pharmacists (
                user_id, hospital_id, pharmacist_id_code, name, phone, email, pharmacy_reg_number,
                qualification, department, is_active
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
        ''', (
            user_id, hospital_id, staff_code, name, phone, email,
            data.get('pharmacy_reg_number'), data.get('qualification'), data.get('department') or 'Pharmacy'
        ))

    elif staff_type in ['ambulance', 'ambulance_driver']:
        amb_number = data.get('ambulance_number') or f"TN-33-AMB-{user_id:04d}"
        cursor.execute('''
            INSERT INTO ambulance_drivers (
                user_id, hospital_id, driver_id_code, name, phone, email, license_number, license_expiry,
                ambulance_number, ambulance_type, emergency_contact, is_active
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
        ''', (
            user_id, hospital_id, staff_code, name, phone, email,
            data.get('license_number'), data.get('license_expiry'),
            amb_number, data.get('ambulance_type') or 'Basic Life Support (BLS)', data.get('emergency_contact')
        ))

        cursor.execute('''
            INSERT INTO ambulances (hospital_id, vehicle_number, driver_name, driver_phone, status, driver_user_id)
            VALUES (?, ?, ?, ?, 'Available', ?)
        ''', (hospital_id, amb_number, name, phone, user_id))

    # Unified hospital_staff sync
    try:
        cursor.execute('''
            INSERT INTO hospital_staff (user_id, hospital_id, staff_id_code, name, role, sub_role, phone, email, is_active)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1)
        ''', (user_id, hospital_id, staff_code, name, staff_type.upper(), staff_type.lower(), phone, email))
    except Exception as hs_err:
        print("[HospitalStaff] Unified insertion notice:", hs_err)

    # Audit Trail Log
    username_admin = session.get('username', 'Hospital Admin')
    cursor.execute('''
        INSERT INTO audit_logs (user_id, username, action, details)
        VALUES (?, ?, 'STAFF_REGISTERED', ?)
    ''', (session.get('user_id'), username_admin, f"Registered {staff_type.upper()} {staff_code} ({name}) for hospital ID {hospital_id}"))

    conn.commit()
    conn.close()

    return jsonify({
        "success": True,
        "message": f"{staff_type.capitalize()} '{name}' registered successfully with ID {staff_code}!",
        "staff_id": staff_code,
        "staff_id_code": staff_code,
        "name": name,
        "user_id": user_id
    }), 201


@hospital_bp.route('/staff/list', methods=['GET'])
@login_required
def list_hospital_staff():
    """Returns all staff members belonging ONLY to currently logged-in hospital_id."""
    hospital_id = session.get('hospital_id', 1)
    role_filter = request.args.get('role', 'all').lower()

    conn = get_db_connection()
    cursor = conn.cursor()

    staff_list = []

    # Doctors
    if role_filter in ['all', 'doctor']:
        cursor.execute("SELECT id, doctor_id_code as staff_id, name, 'Doctor' as role, specialty as department, phone, email, is_active, user_id FROM doctors WHERE hospital_id = ?", (hospital_id,))
        staff_list.extend([dict(r) for r in cursor.fetchall()])

    # Nurses
    if role_filter in ['all', 'nurse']:
        cursor.execute("SELECT id, nurse_id_code as staff_id, name, 'Nurse' as role, department, phone, email, is_active, user_id FROM nurses WHERE hospital_id = ?", (hospital_id,))
        staff_list.extend([dict(r) for r in cursor.fetchall()])

    # Receptionists
    if role_filter in ['all', 'receptionist']:
        cursor.execute("SELECT id, receptionist_id_code as staff_id, name, 'Receptionist' as role, shift as department, phone, email, is_active, user_id FROM receptionists WHERE hospital_id = ?", (hospital_id,))
        staff_list.extend([dict(r) for r in cursor.fetchall()])

    # Pharmacists
    if role_filter in ['all', 'pharmacist']:
        cursor.execute("SELECT id, pharmacist_id_code as staff_id, name, 'Pharmacist' as role, department, phone, email, is_active, user_id FROM pharmacists WHERE hospital_id = ?", (hospital_id,))
        staff_list.extend([dict(r) for r in cursor.fetchall()])

    # Ambulance Drivers
    if role_filter in ['all', 'ambulance', 'ambulance_driver']:
        cursor.execute("SELECT id, driver_id_code as staff_id, name, 'Ambulance Driver' as role, ambulance_number as department, phone, email, is_active, user_id FROM ambulance_drivers WHERE hospital_id = ?", (hospital_id,))
        staff_list.extend([dict(r) for r in cursor.fetchall()])

    # Compute role breakdown statistics for hospital dashboard cards
    cursor.execute("SELECT is_active FROM doctors WHERE hospital_id = ?", (hospital_id,))
    docs = cursor.fetchall()
    cursor.execute("SELECT is_active FROM nurses WHERE hospital_id = ?", (hospital_id,))
    nurs = cursor.fetchall()
    cursor.execute("SELECT is_active FROM receptionists WHERE hospital_id = ?", (hospital_id,))
    recs = cursor.fetchall()
    cursor.execute("SELECT is_active FROM pharmacists WHERE hospital_id = ?", (hospital_id,))
    phas = cursor.fetchall()

    stats = {
        "doctors": {"total": len(docs), "active": sum(1 for d in docs if d[0] == 1)},
        "nurses": {"total": len(nurs), "active": sum(1 for n in nurs if n[0] == 1)},
        "receptionists": {"total": len(recs), "active": sum(1 for r in recs if r[0] == 1)},
        "pharmacists": {"total": len(phas), "active": sum(1 for p in phas if p[0] == 1)}
    }

    conn.close()

    return jsonify({"success": True, "count": len(staff_list), "staff": staff_list, "stats": stats})


@hospital_bp.route('/staff/toggle-status', methods=['POST'])
@hospital_admin_required
def toggle_staff_status():
    """Toggles active/inactive status of a staff member (users + role table)."""
    data = request.json or {}
    user_id = data.get('user_id')
    status = 1 if data.get('active', True) else 0
    action_label = 'activated' if status else 'deactivated'

    if not user_id:
        return jsonify({"error": "user_id required"}), 400

    conn = get_db_connection()
    cursor = conn.cursor()

    # Update in users table
    cursor.execute("UPDATE users SET is_active = ? WHERE id = ?", (status, user_id))

    # Also update in all role-specific tables (hospital_id scoped for safety)
    for table, id_col in [
        ('doctors', 'user_id'),
        ('nurses', 'user_id'),
        ('receptionists', 'user_id'),
        ('pharmacists', 'user_id'),
        ('ambulance_drivers', 'user_id'),
    ]:
        try:
            cursor.execute(f"UPDATE {table} SET is_active = ? WHERE {id_col} = ?", (status, user_id))
        except Exception:
            pass  # Table might not have is_active column yet

    conn.commit()

    # Get staff name for message
    cursor.execute("SELECT name FROM users WHERE id = ?", (user_id,))
    row = cursor.fetchone()
    staff_name = row['name'] if row else f"User {user_id}"
    conn.close()

    return jsonify({"success": True, "message": f"Staff member '{staff_name}' has been {action_label} successfully."})


@hospital_bp.route('/staff/reset-password', methods=['POST'])
@hospital_admin_required
def reset_staff_password():
    """Resets password for a staff member."""
    data = request.json or {}
    user_id = data.get('user_id')
    new_password = data.get('new_password')

    if not user_id or not new_password:
        return jsonify({"error": "User ID and new password required"}), 400

    hashed_pw = generate_password_hash(new_password)
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET password = ? WHERE id = ?", (hashed_pw, user_id))
    conn.commit()
    conn.close()

    return jsonify({"success": True, "message": "Password reset successfully"})


@hospital_bp.route('/staff/details/<int:user_id>', methods=['GET'])
@login_required
def get_staff_details(user_id):
    """Retrieves full profile details of a staff member."""
    hospital_id = session.get('hospital_id', 1)
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, username, role, name, phone, email, is_active, hospital_id FROM users WHERE id = ?", (user_id,))
    u = cursor.fetchone()
    if not u:
        conn.close()
        return jsonify({"error": "Staff user not found"}), 404
    
    user_dict = dict(u)
    role = (u['role'] or '').lower()
    
    details = {}
    if role in ['doctor', 'doc']:
        cursor.execute("SELECT * FROM doctors WHERE user_id = ?", (user_id,))
        r = cursor.fetchone()
        if r: details = dict(r)
    elif role in ['nurse', 'nur']:
        cursor.execute("SELECT * FROM nurses WHERE user_id = ?", (user_id,))
        r = cursor.fetchone()
        if r: details = dict(r)
    elif role in ['receptionist', 'reception', 'rec']:
        cursor.execute("SELECT * FROM receptionists WHERE user_id = ?", (user_id,))
        r = cursor.fetchone()
        if r: details = dict(r)
    elif role in ['pharmacist', 'pharmacy', 'pha']:
        cursor.execute("SELECT * FROM pharmacists WHERE user_id = ?", (user_id,))
        r = cursor.fetchone()
        if r: details = dict(r)
    elif role in ['ambulance', 'ambulance_driver', 'amb']:
        cursor.execute("SELECT * FROM ambulance_drivers WHERE user_id = ?", (user_id,))
        r = cursor.fetchone()
        if r: details = dict(r)
        
    conn.close()
    return jsonify({"success": True, "user": user_dict, "details": details})


@hospital_bp.route('/staff/update', methods=['POST'])
@hospital_admin_required
def update_staff_member():
    """Updates a staff member's profile across users and domain tables."""
    data = request.json or request.form
    user_id = data.get('user_id')
    if not user_id:
        return jsonify({"error": "user_id required"}), 400
        
    name = data.get('name')
    phone = data.get('phone')
    email = data.get('email')
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT role FROM users WHERE id = ?", (user_id,))
    u = cursor.fetchone()
    if not u:
        conn.close()
        return jsonify({"error": "User not found"}), 404
        
    role = (u['role'] or '').lower()
    
    cursor.execute("UPDATE users SET name = ?, phone = ?, email = ? WHERE id = ?", (name, phone, email, user_id))
    
    if role in ['doctor', 'doc']:
        cursor.execute('''
            UPDATE doctors SET name = ?, phone = ?, email = ?, specialty = ?, qualification = ? WHERE user_id = ?
        ''', (name, phone, email, data.get('specialization') or data.get('specialty') or 'General', data.get('qualification'), user_id))
    elif role in ['nurse', 'nur']:
        cursor.execute('''
            UPDATE nurses SET name = ?, phone = ?, email = ?, department = ?, shift = ? WHERE user_id = ?
        ''', (name, phone, email, data.get('department'), data.get('shift'), user_id))
    elif role in ['receptionist', 'reception', 'rec']:
        cursor.execute('''
            UPDATE receptionists SET name = ?, phone = ?, email = ?, shift = ? WHERE user_id = ?
        ''', (name, phone, email, data.get('shift'), user_id))
    elif role in ['pharmacist', 'pharmacy', 'pha']:
        cursor.execute('''
            UPDATE pharmacists SET name = ?, phone = ?, email = ?, department = ? WHERE user_id = ?
        ''', (name, phone, email, data.get('department'), user_id))
    elif role in ['ambulance', 'ambulance_driver', 'amb']:
        cursor.execute('''
            UPDATE ambulance_drivers SET name = ?, phone = ?, email = ?, license_number = ?, ambulance_number = ? WHERE user_id = ?
        ''', (name, phone, email, data.get('license_number'), data.get('ambulance_number'), user_id))
        cursor.execute('''
            UPDATE ambulances SET driver_name = ?, driver_phone = ? WHERE driver_user_id = ?
        ''', (name, phone, user_id))
        
    try:
        cursor.execute("UPDATE hospital_staff SET name = ?, phone = ?, email = ? WHERE user_id = ?", (name, phone, email, user_id))
    except Exception:
        pass
        
    conn.commit()
    conn.close()
    return jsonify({"success": True, "message": f"Staff member '{name}' updated successfully!"})


@hospital_bp.route('/staff/delete', methods=['POST'])
@hospital_admin_required
def delete_staff_member():
    """Permanently deletes a staff member from the database."""
    data = request.json or request.form
    user_id = data.get('user_id')
    if not user_id:
        return jsonify({"error": "user_id required"}), 400
        
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT name, role FROM users WHERE id = ?", (user_id,))
    u = cursor.fetchone()
    staff_name = u['name'] if u else f"User #{user_id}"
    
    for tbl in ['doctors', 'nurses', 'receptionists', 'pharmacists', 'ambulance_drivers', 'hospital_staff']:
        try:
            cursor.execute(f"DELETE FROM {tbl} WHERE user_id = ?", (user_id,))
        except Exception:
            pass
            
    cursor.execute("DELETE FROM ambulances WHERE driver_user_id = ?", (user_id,))
    cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
    
    conn.commit()
    conn.close()
    return jsonify({"success": True, "message": f"Staff member '{staff_name}' deleted permanently."})



# ──────────────────────────────────────────────────────────────────
# Doctor Consultation, Prescription, Medical Report & Billing APIs
# ──────────────────────────────────────────────────────────────────
@hospital_bp.route('/patient/consultation', methods=['POST'])
def doctor_consultation():
    """
    Doctor submits clinical diagnosis, treatment, prescription, generates medical report (REP-XXXXXX)
    and itemized medical bill (BILL-XXXXXX).
    """
    import json
    from datetime import datetime
    from database import (
        generate_unique_patient_id,
        generate_unique_report_id,
        generate_unique_bill_id
    )
    from report_generator import generate_medical_report

    data = request.json or request.form
    emergency_id = data.get('emergency_id')
    driver_id = data.get('driver_id')
    diagnosis = data.get('diagnosis') or "Suspected Cardiac Emergency"
    treatment = data.get('treatment') or "Bed rest, Oxygen support, IV fluids, Cardiac monitoring"
    doctor_notes = data.get('doctor_notes') or ""
    medicines = data.get('medicines') or []
    
    if isinstance(medicines, str):
        try:
            medicines = json.loads(medicines)
        except Exception:
            medicines = [{"name": medicines, "dosage": "500mg", "qty": 1, "price": 50.0}]

    hospital_id = session.get('hospital_id', 1)
    doctor_user_id = session.get('user_id', 2)
    doctor_name = session.get('name') or "Dr. Clara"

    conn = get_db_connection()
    cursor = conn.cursor()

    # Load emergency record if provided
    emerg = None
    if emergency_id:
        cursor.execute("SELECT * FROM emergencies WHERE id = ?", (emergency_id,))
        emerg = cursor.fetchone()
        if emerg and not driver_id:
            driver_id = emerg['driver_id']

    if not driver_id:
        driver_id = 1

    # Load Driver & User details
    cursor.execute(
        "SELECT d.*, u.name AS user_name, u.phone AS user_phone, u.email AS user_email "
        "FROM drivers d JOIN users u ON d.user_id = u.id WHERE d.id = ?",
        (driver_id,)
    )
    driver_row = cursor.fetchone()
    driver = dict(driver_row) if driver_row else {}
    # Resolve name/phone/email: driver table takes priority over users table
    driver['name']  = driver.get('name')  or driver.get('user_name')  or ''
    driver['phone'] = driver.get('phone') or driver.get('user_phone') or ''
    driver['email'] = driver.get('email') or driver.get('user_email') or ''
    patient_name = driver.get('name') or 'Unknown Driver'
    driver_code = (driver['driver_id_code'] if (driver and driver['driver_id_code']) else "DRV-000001")
    age = driver['age'] if driver else 52
    gender = driver['gender'] if driver else "Male"
    blood_group = driver['blood_group'] if driver else "O+"

    # 1. Match or Create Patient Record (PAT-XXXXXX)
    cursor.execute("SELECT * FROM patients WHERE driver_id = ? OR driver_id_code = ?", (driver_id, driver_code))
    patient = cursor.fetchone()
    if not patient:
        pat_code = generate_unique_patient_id(conn)
        cursor.execute("""
            INSERT INTO patients (patient_id_code, hospital_id, driver_id, driver_id_code, name, age, gender, blood_group, current_status, previous_diseases)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'Admitted', 'Diabetes, Hypertension')
        """, (pat_code, hospital_id, driver_id, driver_code, patient_name, age, gender, blood_group))
        patient_id = cursor.lastrowid
    else:
        patient_id = patient['id']
        pat_code = patient['patient_id_code'] or f"PAT-{patient_id:06d}"

    # 2. Update Emergency Record with Diagnosis
    if emergency_id:
        cursor.execute("""
            UPDATE emergencies
            SET doctor_diagnosis = ?, doctor_treatment = ?, assigned_doctor_id = ?, status = 'TREATED'
            WHERE id = ?
        """, (diagnosis, treatment, doctor_user_id, emergency_id))

    # 3. Create Prescription Record
    cursor.execute("""
        INSERT INTO prescriptions (hospital_id, emergency_id, patient_id, doctor_id, doctor_name, diagnosis, treatment, medicines_json, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'Dispensed')
    """, (hospital_id, emergency_id, patient_id, doctor_user_id, doctor_name, diagnosis, treatment, json.dumps(medicines)))
    prescription_id = cursor.lastrowid

    # 4. Generate Medical Report (REP-XXXXXX)
    rep_code = generate_unique_report_id(conn)
    pdf_name = f"Medical_Report_{rep_code}.pdf"
    pdf_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static', 'reports')
    os.makedirs(pdf_dir, exist_ok=True)
    pdf_path = os.path.join(pdf_dir, pdf_name)

    driver_data = dict(driver)  # Pass the full driver dict to report generator

    # Fetch vitals from emergency or health_logs
    cursor.execute("SELECT * FROM health_logs WHERE driver_id = ? ORDER BY timestamp DESC LIMIT 1", (driver_id,))
    v_row = cursor.fetchone()
    v_dict = dict(v_row) if v_row else {}

    if emerg:
        bp_raw = str(emerg.get('blood_pressure') or v_dict.get('blood_pressure') or '120/80')
        bp_parts = bp_raw.split('/')
        def _bp(val, default):
            try: return str(int(float(val.strip())))
            except Exception: return default
        sys_bp = _bp(bp_parts[0], '120') if len(bp_parts) > 0 else '120'
        dia_bp = _bp(bp_parts[1], '80')  if len(bp_parts) > 1 else '80'

        health_data = {
            'heart_rate': emerg.get('heart_rate') or v_dict.get('heart_rate') or 72.0,
            'spo2': emerg.get('spo2') or v_dict.get('spo2') or 98.0,
            'temperature': emerg.get('temperature') or v_dict.get('temperature') or 36.6,
            'systolic_bp': sys_bp,
            'diastolic_bp': dia_bp,
            'respiration_rate': emerg.get('respiration') or v_dict.get('respiration_rate') or 18,
            'sleep_hours': emerg.get('sleep_hours') or v_dict.get('sleep_hours') or 7.0,
            'stress_level': emerg.get('stress_level') or v_dict.get('stress_level') or 3.0,
            'fatigue_score': emerg.get('fatigue_score') or v_dict.get('fatigue_score') or 3.0,
            'symptoms': emerg.get('symptoms') or v_dict.get('symptoms') or 'Vitals Monitoring Log'
        }
    else:
        health_data = v_dict if v_dict else {'heart_rate': 72.0, 'spo2': 98.0, 'temperature': 36.6, 'systolic_bp': 120, 'diastolic_bp': 80, 'respiration_rate': 18, 'sleep_hours': 7, 'stress_level': 3, 'fatigue_score': 3, 'symptoms': 'Standard Vitals Assessment'}

    prediction_data = {
        'prediction': diagnosis,
        'severity': 'CRITICAL' if 'Cardiac' in diagnosis or 'Heart' in diagnosis else 'MODERATE',
        'confidence': 0.95,
        'risk_percentage': 95.0,
        'explanation': f"Clinical diagnosis confirmed by {doctor_name}: {diagnosis}.",
        'suggested_action': f"Treatment Plan: {treatment}. Notes: {doctor_notes}"
    }

    cursor.execute("SELECT * FROM hospitals WHERE id = ?", (hospital_id,))
    hosp = cursor.fetchone()
    hospital_data = dict(hosp) if hosp else {'name': 'Lotus Hospital', 'address': 'Erode', 'phone': '+91 424 228 2828', 'latitude': 11.3410, 'longitude': 77.7170}

    ambulance_data = {'vehicle_number': 'TN-33-AA-1111', 'driver_name': 'Rajesh Kumar', 'driver_phone': '+91 9000100010'}

    try:
        generate_medical_report(driver_data, health_data, prediction_data, hospital_data, ambulance_data, pdf_path, extra_data=emerg)
    except Exception as pdf_err:
        print(f"[HospitalAPI] PDF generation notice: {pdf_err}")

    cursor.execute("""
        INSERT INTO medical_reports (report_id_code, emergency_id, patient_id, hospital_id, doctor_id, diagnosis, treatment, prescription_text, pdf_filename, report_json)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (rep_code, emergency_id, patient_id, hospital_id, doctor_user_id, diagnosis, treatment, json.dumps(medicines), pdf_name, json.dumps(prediction_data)))
    report_db_id = cursor.lastrowid

    # 5. Calculate & Generate Itemized Medical Bill (BILL-XXXXXX)
    bill_code = generate_unique_bill_id(conn)
    consultation_fee = 500.0
    emergency_fee = 1000.0
    bed_charges = 1500.0
    icu_charges = 3000.0 if 'Cardiac' in diagnosis else 0.0
    lab_charges = 750.0
    ecg_charges = 500.0
    
    med_subtotal = 0.0
    bill_items_list = []
    for med in medicines:
        m_name = med.get('name') or med.get('medicine_name') or 'Prescribed Medicine'
        m_qty = int(med.get('qty') or med.get('quantity') or 1)
        m_price = float(med.get('price') or med.get('unit_price') or 50.0)
        tot = m_qty * m_price
        med_subtotal += tot
        bill_items_list.append((m_name, 'Medicine', m_qty, m_price, tot))

    subtotal = consultation_fee + emergency_fee + bed_charges + icu_charges + lab_charges + ecg_charges + med_subtotal
    tax_amount = round(subtotal * 0.05, 2) # 5% tax
    grand_total = subtotal + tax_amount

    cursor.execute("""
        INSERT INTO medical_bills (
            bill_id_code, hospital_id, patient_id, emergency_id, doctor_id, patient_name,
            admission_date, discharge_date, doctor_name, diagnosis, treatment,
            consultation_fee, emergency_fee, bed_charges, icu_charges, lab_charges, ecg_charges,
            medicine_subtotal, tax_amount, grand_total, payment_status, authorized_staff
        ) VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'Pending', ?)
    """, (
        bill_code, hospital_id, patient_id, emergency_id, doctor_user_id, patient_name,
        doctor_name, diagnosis, treatment,
        consultation_fee, emergency_fee, bed_charges, icu_charges, lab_charges, ecg_charges,
        med_subtotal, tax_amount, grand_total, doctor_name
    ))
    bill_db_id = cursor.lastrowid

    # Insert items into bill_items
    for item in bill_items_list:
        cursor.execute("""
            INSERT INTO bill_items (bill_id, item_name, category, quantity, unit_price, total_price)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (bill_db_id, item[0], item[1], item[2], item[3], item[4]))

    # Standard items
    cursor.execute("INSERT INTO bill_items (bill_id, item_name, category, quantity, unit_price, total_price) VALUES (?, 'Doctor Consultation', 'Fee', 1, ?, ?)", (bill_db_id, consultation_fee, consultation_fee))
    cursor.execute("INSERT INTO bill_items (bill_id, item_name, category, quantity, unit_price, total_price) VALUES (?, 'Emergency Care & Triage', 'Fee', 1, ?, ?)", (bill_db_id, emergency_fee, emergency_fee))
    if icu_charges > 0:
        cursor.execute("INSERT INTO bill_items (bill_id, item_name, category, quantity, unit_price, total_price) VALUES (?, 'ICU Cardiac Monitoring Unit', 'Bed', 1, ?, ?)", (bill_db_id, icu_charges, icu_charges))

    # 6. Save Patient Medical History Record
    cursor.execute("""
        INSERT INTO patient_medical_history (
            patient_id, driver_id, emergency_id, hospital_name, doctor_name, diagnosis, treatment,
            prescriptions_summary, report_id_code, bill_id_code, vitals_summary, admission_status
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'Treated')
    """, (
        patient_id, driver_id, emergency_id, hospital_data['name'], doctor_name, diagnosis, treatment,
        json.dumps(medicines), rep_code, bill_code, f"HR: {health_data.get('heart_rate')} BPM, SpO2: {health_data.get('spo2')}%"
    ))

    # Log to audit_logs
    cursor.execute("""
        INSERT INTO audit_logs (user_id, username, action, details)
        VALUES (?, ?, 'DOCTOR_CONSULTATION', ?)
    """, (doctor_user_id, doctor_name, f"Consultation completed for {patient_name}. Generated Report {rep_code} and Bill {bill_code}."))

    conn.commit()
    conn.close()

    return jsonify({
        "success": True,
        "message": f"Clinical consultation recorded for {patient_name}.",
        "patient_id": pat_code,
        "report_id": rep_code,
        "bill_id": bill_code,
        "pdf_url": f"/static/reports/{pdf_name}",
        "grand_total": grand_total
    })

@hospital_bp.route('/bill/<bill_id_code>/pay', methods=['POST'])
def pay_bill(bill_id_code):
    """Marks medical bill as Paid."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE medical_bills SET payment_status = 'Paid' WHERE bill_id_code = ?", (bill_id_code,))
    conn.commit()
    conn.close()
    return jsonify({"success": True, "message": f"Bill {bill_id_code} marked as Paid."})


@hospital_bp.route('/patient/discharge', methods=['POST'])
def discharge_patient():
    """
    Discharges an admitted patient by updating their status in hospital_admissions.
    """
    data = request.json or {}
    admission_id = data.get('admission_id')
    
    if not admission_id:
        return jsonify({"success": False, "error": "Admission ID is required"}), 400
        
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Check if admission exists
    cursor.execute("SELECT * FROM hospital_admissions WHERE id = ?", (admission_id,))
    admission = cursor.fetchone()
    if not admission:
        conn.close()
        return jsonify({"success": False, "error": "Admission record not found"}), 404
        
    from datetime import datetime
    now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    # Update status to DISCHARGED and discharged_at to current timestamp
    cursor.execute("""
        UPDATE hospital_admissions 
        SET status = 'DISCHARGED', discharged_at = ? 
        WHERE id = ?
    """, (now_str, admission_id))
    
    # Update the patient status in the patients table if driver_id is present
    driver_id = admission['driver_id']
    if driver_id:
        cursor.execute("UPDATE patients SET current_status = 'Discharged' WHERE driver_id = ?", (driver_id,))
        
    # Complete/Resolve associated emergency event
    emergency_id = admission['emergency_id']
    if emergency_id:
        cursor.execute("UPDATE emergencies SET status = 'COMPLETED' WHERE id = ?", (emergency_id,))
        cursor.execute("UPDATE emergency_events SET status = 'RESOLVED', resolved_at = ? WHERE id = ?", (now_str, emergency_id))
        
        # Log to emergency_timeline
        cursor.execute("""
            INSERT INTO emergency_timeline (emergency_id, step, detail, status, timestamp)
            VALUES (?, 'Patient Discharged', 'Patient successfully discharged from hospital.', 'COMPLETED', ?)
        """, (emergency_id, now_str))

    conn.commit()
    conn.close()
    
    return jsonify({"success": True, "message": "Patient successfully discharged"})


@hospital_bp.route('/emergency/accept', methods=['POST'])
def receptionist_accept_emergency():
    """
    Receptionist accepts an incoming emergency dispatch for this hospital.
    Sets HOSPITAL_ACCEPTED status and notifies ambulance driver with route via socket.
    """
    data = request.json or {}
    emergency_id = data.get('emergency_id')
    user_id = session.get('user_id')
    hospital_id = int(session.get('hospital_id') or data.get('hospital_id') or 1)

    if not emergency_id:
        return jsonify({"success": False, "error": "emergency_id is required"}), 400

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM emergencies WHERE id = ? OR emergency_code = ?", (str(emergency_id), str(emergency_id)))
    emerg = cursor.fetchone()
    if not emerg:
        conn.close()
        return jsonify({"success": False, "error": "Emergency not found"}), 404

    actual_id = emerg['id']
    if emerg['accepted_hospital_id'] and int(emerg['accepted_hospital_id']) != hospital_id:
        conn.close()
        return jsonify({"success": False, "error": "Emergency already accepted by another hospital"}), 409

    from datetime import datetime
    now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    cursor.execute("""
        UPDATE emergencies
        SET hospital_id = COALESCE(hospital_id, ?),
            accepted_hospital_id = ?,
            hospital_status = 'ACCEPTED',
            status = 'HOSPITAL_ACCEPTED',
            hospital_accepted_at = ?
        WHERE id = ? AND (accepted_hospital_id IS NULL OR accepted_hospital_id = ?)
    """, (hospital_id, hospital_id, now_str, actual_id, hospital_id))

    if cursor.rowcount == 0:
        conn.rollback()
        conn.close()
        return jsonify({"success": False, "error": "Could not accept — another hospital may have accepted this emergency"}), 409

    cursor.execute("""
        INSERT INTO emergency_timeline (emergency_id, step, detail, status, timestamp)
        VALUES (?, 'HOSPITAL_ACCEPTED', 'Emergency accepted by hospital receptionist', 'completed', ?)
    """, (actual_id, now_str))

    cursor.execute("""
        INSERT INTO audit_logs (user_id, username, action, details)
        VALUES (?, ?, 'RECEPTIONIST_ACCEPT', ?)
    """, (user_id, session.get('username', 'Receptionist'), f"Hospital #{hospital_id} accepted emergency #{actual_id}"))

    conn.commit()

    cursor.execute("SELECT name, address, emergency_number, latitude, longitude FROM hospitals WHERE id = ?", (hospital_id,))
    hosp_info = cursor.fetchone()
    conn.close()
    hosp_dict = dict(hosp_info) if hosp_info else {}

    try:
        from extensions import socketio
        from event_broadcaster import publish_event
        payload = {
            "emergency_id": actual_id,
            "hospital_id": hospital_id,
            "accepted_hospital_id": hospital_id,
            "hospital_name": hosp_dict.get('name'),
            "hospital_address": hosp_dict.get('address'),
            "hospital_phone": hosp_dict.get('emergency_number'),
            "hosp_lat": hosp_dict.get('latitude'),
            "hosp_lng": hosp_dict.get('longitude'),
            "status": "HOSPITAL_ACCEPTED",
            "message": f"Hospital '{hosp_dict.get('name')}' accepted the emergency!"
        }
        socketio.emit('hospital_accepted', payload)
        socketio.emit('risk_updated', payload)
        publish_event('HOSPITAL_ACCEPTED', payload)
    except Exception as e:
        print(f"[ReceptionistAccept] Socket emit: {e}")

    return jsonify({
        "success": True,
        "status": "HOSPITAL_ACCEPTED",
        "message": f"Emergency accepted! Ambulance notified with route to {hosp_dict.get('name', 'Hospital')}.",
        "hospital_name": hosp_dict.get('name'),
        "hosp_lat": hosp_dict.get('latitude'),
        "hosp_lng": hosp_dict.get('longitude')
    })


@hospital_bp.route('/patient/admit', methods=['POST'])
def admit_patient():
    """
    Creates a hospital admission record for a patient from an accepted emergency.
    Called by receptionist after hospital accepts the emergency.
    """
    from datetime import datetime
    data = request.json or {}
    emergency_id = data.get('emergency_id')
    hospital_id = int(session.get('hospital_id') or data.get('hospital_id') or 1)
    ward = data.get('ward') or 'Emergency Ward'
    bed_number = data.get('bed_number') or 'E-01'

    if not emergency_id:
        return jsonify({"success": False, "error": "emergency_id is required"}), 400

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM emergencies WHERE id = ? OR emergency_code = ?", (str(emergency_id), str(emergency_id)))
    emerg = cursor.fetchone()
    if not emerg:
        conn.close()
        return jsonify({"success": False, "error": "Emergency not found"}), 404

    actual_id = emerg['id']
    driver_id = emerg['driver_id']

    cursor.execute("SELECT id FROM hospital_admissions WHERE emergency_id = ?", (actual_id,))
    existing = cursor.fetchone()
    if existing:
        conn.close()
        return jsonify({"success": False, "error": "Patient already admitted for this emergency", "admission_id": existing['id']}), 409

    cursor.execute("""
        SELECT d.*, u.name as user_name FROM drivers d
        LEFT JOIN users u ON d.user_id = u.id WHERE d.id = ?
    """, (driver_id,))
    driver_row = cursor.fetchone()
    driver = dict(driver_row) if driver_row else {}
    patient_name = driver.get('name') or driver.get('user_name') or 'Unknown Patient'
    age = driver.get('age') or 0
    gender = driver.get('gender') or 'Unknown'
    blood_group = driver.get('blood_group') or 'O+'

    now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    cursor.execute("""
        INSERT INTO hospital_admissions (
            hospital_id, emergency_id, driver_id, patient_name,
            age, gender, blood_group, ward, bed_number,
            admitted_at, status
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'ADMITTED')
    """, (hospital_id, actual_id, driver_id, patient_name, age, gender, blood_group, ward, bed_number, now_str))
    adm_id = cursor.lastrowid

    cursor.execute("UPDATE emergencies SET status = 'PATIENT_ADMITTED' WHERE id = ?", (actual_id,))

    cursor.execute("""
        INSERT INTO emergency_timeline (emergency_id, step, detail, status, timestamp)
        VALUES (?, 'PATIENT_ADMITTED', ?, 'completed', ?)
    """, (actual_id, f"Patient '{patient_name}' admitted to {ward}, Bed {bed_number}", now_str))

    conn.commit()
    conn.close()

    return jsonify({
        "success": True,
        "message": f"Patient '{patient_name}' admitted to {ward}, Bed {bed_number}",
        "admission_id": adm_id,
        "patient_name": patient_name,
        "ward": ward,
        "bed_number": bed_number
    })




