from database import init_db as raw_init_db, get_db_connection, seed_erode_hospitals
from werkzeug.security import generate_password_hash

def make_hash(pwd):
    return generate_password_hash(pwd, method='pbkdf2:sha256')

def seed_db():
    print("Initializing database tables...")
    raw_init_db()

    conn = get_db_connection()
    cursor = conn.cursor()

    # Seed Erode District Hospitals
    seed_erode_hospitals(conn)

    # 1. System Admin
    cursor.execute("SELECT id FROM users WHERE username = 'admin'")
    if not cursor.fetchone():
        cursor.execute('''
            INSERT INTO users (username, password, role, name, phone, email, verified)
            VALUES ('admin', ?, 'admin', 'System Administrator', '+91 9876500000', 'admin@aiguardian.org', 1)
        ''', (make_hash('admin123'),))
    else:
        cursor.execute("UPDATE users SET password = ? WHERE username = 'admin'", (make_hash('admin123'),))

    # 2. Driver
    cursor.execute("SELECT id FROM users WHERE username = 'driver1'")
    row_d1 = cursor.fetchone()
    if not row_d1:
        cursor.execute('''
            INSERT INTO users (username, password, role, name, phone, email, verified)
            VALUES ('driver1', ?, 'driver', 'Lithhish Driver', '+91 9876511111', 'driver@aiguardian.org', 1)
        ''', (make_hash('password123'),))
        u_drv = cursor.lastrowid
        cursor.execute('''
            INSERT INTO drivers (user_id, driver_id_code, age, gender, blood_group, vehicle_number, medical_history)
            VALUES (?, 'DRV000001', 32, 'Male', 'O+', 'TN-33-AX-1234', 'None')
        ''', (u_drv,))
    else:
        cursor.execute("UPDATE users SET password = ? WHERE username = 'driver1'", (make_hash('password123'),))

    # Also support legacy driver username 'LITHHISH'
    cursor.execute("SELECT id FROM users WHERE username = 'LITHHISH'")
    if not cursor.fetchone():
        cursor.execute('''
            INSERT INTO users (username, password, role, name, phone, email, verified)
            VALUES ('LITHHISH', ?, 'driver', 'LITHHISH Driver', '+91 9876511112', 'lithhish@aiguardian.org', 1)
        ''', (make_hash('driver123'),))
    else:
        cursor.execute("UPDATE users SET password = ? WHERE username = 'LITHHISH'", (make_hash('driver123'),))

    # 3. Hospital Admin (Lotus Hospital - Hospital ID 1)
    cursor.execute("SELECT id FROM users WHERE username = 'hospital1'")
    if not cursor.fetchone():
        cursor.execute('''
            INSERT INTO users (username, password, role, name, phone, email, hospital_id, verified)
            VALUES ('hospital1', ?, 'hospital', 'Lotus Hospital Admin', '+91 424 228 2828', 'admin@lotushospital.org', 1, 1)
        ''', (make_hash('password123'),))
    else:
        cursor.execute("UPDATE users SET password = ?, role = 'hospital', hospital_id = 1 WHERE username = 'hospital1'", (make_hash('password123'),))

    # 3b. Hospital Admin (Thangam Hospital - Hospital ID 2)
    cursor.execute("SELECT id FROM users WHERE username = 'hospital2'")
    if not cursor.fetchone():
        cursor.execute('''
            INSERT INTO users (username, password, role, name, phone, email, hospital_id, verified)
            VALUES ('hospital2', ?, 'hospital', 'Thangam Hospital Admin', '+91 424 222 5555', 'admin@thangamhospital.com', 2, 1)
        ''', (make_hash('password123'),))
    else:
        cursor.execute("UPDATE users SET password = ?, role = 'hospital', hospital_id = 2 WHERE username = 'hospital2'", (make_hash('password123'),))

    # 4. Doctor
    cursor.execute("SELECT id FROM users WHERE username = 'doctor1'")
    if not cursor.fetchone():
        cursor.execute('''
            INSERT INTO users (username, password, role, name, phone, email, hospital_id, verified)
            VALUES ('doctor1', ?, 'doctor', 'Dr. S. Vignesh', '+91 9876522222', 'vignesh@lotushospital.org', 1, 1)
        ''', (make_hash('password123'),))
        u_doc = cursor.lastrowid
        cursor.execute("SELECT id FROM doctors WHERE doctor_id_code = 'DOC000001'")
        if not cursor.fetchone():
            cursor.execute('''
                INSERT INTO doctors (user_id, hospital_id, doctor_id_code, name, phone, email, specialty, qualification, experience, emergency_dept)
                VALUES (?, 1, 'DOC000001', 'Dr. S. Vignesh', '+91 9876522222', 'vignesh@lotushospital.org', 'Cardiology', 'MD, DM (Cardiology)', '12 Years', 'Cardiac ER')
            ''', (u_doc,))
    else:
        cursor.execute("UPDATE users SET password = ?, role = 'doctor', hospital_id = 1 WHERE username = 'doctor1'", (make_hash('password123'),))

    # 5. Nurse
    cursor.execute("SELECT id FROM users WHERE username = 'nurse1'")
    if not cursor.fetchone():
        cursor.execute('''
            INSERT INTO users (username, password, role, name, phone, email, hospital_id, verified)
            VALUES ('nurse1', ?, 'nurse', 'Nurse Priya', '+91 9876533333', 'priya@lotushospital.org', 1, 1)
        ''', (make_hash('password123'),))
        u_nur = cursor.lastrowid
        cursor.execute("SELECT id FROM nurses WHERE nurse_id_code = 'NUR000001'")
        if not cursor.fetchone():
            cursor.execute('''
                INSERT INTO nurses (user_id, hospital_id, nurse_id_code, name, phone, email, qualification, department, shift)
                VALUES (?, 1, 'NUR000001', 'Nurse Priya', '+91 9876533333', 'priya@lotushospital.org', 'B.Sc Nursing', 'ICU Care', 'Day')
            ''', (u_nur,))
    else:
        cursor.execute("UPDATE users SET password = ?, role = 'nurse', hospital_id = 1 WHERE username = 'nurse1'", (make_hash('password123'),))

    # 6. Receptionist
    cursor.execute("SELECT id FROM users WHERE username = 'receptionist1'")
    if not cursor.fetchone():
        cursor.execute('''
            INSERT INTO users (username, password, role, name, phone, email, hospital_id, verified)
            VALUES ('receptionist1', ?, 'receptionist', 'Rec. Lakshmi', '+91 9876544444', 'reception@lotushospital.org', 1, 1)
        ''', (make_hash('password123'),))
        u_rec = cursor.lastrowid
        cursor.execute("SELECT id FROM receptionists WHERE receptionist_id_code = 'REC000001'")
        if not cursor.fetchone():
            cursor.execute('''
                INSERT INTO receptionists (user_id, hospital_id, receptionist_id_code, name, phone, email, shift)
                VALUES (?, 1, 'REC000001', 'Rec. Lakshmi', '+91 9876544444', 'reception@lotushospital.org', 'Day')
            ''', (u_rec,))
    else:
        cursor.execute("UPDATE users SET password = ?, role = 'receptionist', hospital_id = 1 WHERE username = 'receptionist1'", (make_hash('password123'),))

    # 7. Pharmacist
    cursor.execute("SELECT id FROM users WHERE username = 'pharmacist1'")
    if not cursor.fetchone():
        cursor.execute('''
            INSERT INTO users (username, password, role, name, phone, email, hospital_id, verified)
            VALUES ('pharmacist1', ?, 'pharmacist', 'Pharm. Suresh', '+91 9876555555', 'pharmacy@lotushospital.org', 1, 1)
        ''', (make_hash('password123'),))
        u_pha = cursor.lastrowid
        cursor.execute("SELECT id FROM pharmacists WHERE pharmacist_id_code = 'PHA000001'")
        if not cursor.fetchone():
            cursor.execute('''
                INSERT INTO pharmacists (user_id, hospital_id, pharmacist_id_code, name, phone, email, qualification, department)
                VALUES (?, 1, 'PHA000001', 'Pharm. Suresh', '+91 9876555555', 'pharmacy@lotushospital.org', 'B.Pharm', 'Pharmacy')
            ''', (u_pha,))
    else:
        cursor.execute("UPDATE users SET password = ?, role = 'pharmacist', hospital_id = 1 WHERE username = 'pharmacist1'", (make_hash('password123'),))

    # 8. Ambulance Driver
    cursor.execute("SELECT id FROM users WHERE username = 'ambulance1'")
    if not cursor.fetchone():
        cursor.execute('''
            INSERT INTO users (username, password, role, name, phone, email, hospital_id, verified)
            VALUES ('ambulance1', ?, 'ambulance', 'Driver Murugan', '+91 9876566666', 'ambulance@lotushospital.org', 1, 1)
        ''', (make_hash('password123'),))
        u_amb = cursor.lastrowid
        cursor.execute("SELECT id FROM ambulance_drivers WHERE driver_id_code = 'AMB000001'")
        if not cursor.fetchone():
            cursor.execute('''
                INSERT INTO ambulance_drivers (user_id, hospital_id, driver_id_code, name, phone, email, ambulance_number, ambulance_type)
                VALUES (?, 1, 'AMB000001', 'Driver Murugan', '+91 9876566666', 'ambulance@lotushospital.org', 'TN-33-AMB-01', 'Advanced Life Support (ALS)')
            ''', (u_amb,))
        cursor.execute("SELECT id FROM ambulances WHERE vehicle_number = 'TN-33-AMB-01'")
        if not cursor.fetchone():
            cursor.execute('''
                INSERT INTO ambulances (hospital_id, vehicle_number, driver_name, driver_phone, status, driver_user_id, latitude, longitude)
                VALUES (1, 'TN-33-AMB-01', 'Driver Murugan', '+91 9876566666', 'Available', ?, 11.3410, 77.7170)
            ''', (u_amb,))
    else:
        cursor.execute("UPDATE users SET password = ?, role = 'ambulance', hospital_id = 1 WHERE username = 'ambulance1'", (make_hash('password123'),))

    # 9. Family Member
    cursor.execute("SELECT id FROM users WHERE username = 'family1'")
    fam_user_row = cursor.fetchone()
    if not fam_user_row:
        cursor.execute('''
            INSERT INTO users (username, password, role, name, phone, email, verified)
            VALUES ('family1', ?, 'family', 'Kavitha (Family)', '+91 9876577777', 'family@aiguardian.org', 1)
        ''', (make_hash('password123'),))
        u_fam = cursor.lastrowid
    else:
        u_fam = fam_user_row['id']
        cursor.execute("UPDATE users SET password = ?, role = 'family' WHERE id = ?", (make_hash('password123'), u_fam))

    cursor.execute("SELECT id FROM family_members WHERE driver_id = 1 OR driver_id_code = 'DRV000001' OR driver_id_code = 'DRV-000001'")
    if not cursor.fetchone():
        cursor.execute('''
            INSERT INTO family_members (user_id, driver_id, driver_id_code, family_id_code, name, phone, email, relation, status)
            VALUES (?, 1, 'DRV-000001', 'FAM-000001', 'Kavitha (Family)', '+91 9876577777', 'family@aiguardian.org', 'Spouse', 'ACTIVE')
        ''', (u_fam,))
    else:
        cursor.execute('''
            UPDATE family_members SET driver_id = 1, driver_id_code = 'DRV-000001', family_id_code = 'FAM-000001',
            name = 'Kavitha (Family)', phone = '+91 9876577777', status = 'ACTIVE' WHERE user_id = ?
        ''', (u_fam,))

    # 10. Demo Emergency Assigned to Hospital ID 1 (Lotus Hospital)
    cursor.execute("SELECT id FROM emergencies WHERE hospital_id = 1")
    if not cursor.fetchone():
        cursor.execute('''
            INSERT INTO emergencies (driver_id, prediction, confidence, risk_percentage, severity, explanation, suggested_action, hospital_id, accepted_hospital_id, status, driver_lat, driver_lng)
            VALUES (1, 'Possible Cardiac Emergency', 0.89, 89.0, 'CRITICAL', 'AI Health Risk Detection: Tachycardia and severe chest tightness', 'Immediate ER Prep and Cardiac Cath Lab standby', 1, 1, 'Active', 11.3410, 77.7170)
        ''')

    conn.commit()
    conn.close()
    print("Database initialized and seeded with demo accounts for all roles successfully.")

if __name__ == '__main__':
    seed_db()
