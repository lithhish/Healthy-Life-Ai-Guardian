from flask import Blueprint, render_template, session, redirect, url_for, flash, request
from functools import wraps

main_bp = Blueprint('main', __name__)

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('auth.login', role='driver'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session or session.get('role') != 'admin':
            return "Access Denied: Admin privileges required", 403
        return f(*args, **kwargs)
    return decorated_function

def hospital_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session or not session.get('hospital_id'):
            return redirect(url_for('auth.hospital_login'))
        allowed = ['hospital', 'hospital_admin', 'doctor', 'nurse', 'receptionist', 'pharmacist', 'ambulance', 'ambulance_driver', 'staff', 'admin']
        if session.get('role') not in allowed:
            return redirect(url_for('auth.hospital_login'))
        return f(*args, **kwargs)
    return decorated_function

@main_bp.route('/')
def home():
    return render_template('home.html')

@main_bp.route('/erode-hospitals')
def erode_hospitals():
    """Erode District Google Maps & Specialist Hospital Discovery Page"""
    return render_template('erode_hospitals.html')

@main_bp.route('/dashboard/driver')
@login_required
def driver_dashboard():
    from database import get_db_connection, generate_unique_driver_id
    user_id = session.get('user_id')
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT d.*, u.name as user_name, u.phone as user_phone, u.email as user_email, u.username
        FROM drivers d
        LEFT JOIN users u ON d.user_id = u.id
        WHERE d.user_id = ? OR u.id = ?
    ''', (user_id, user_id))
    driver_row = cursor.fetchone()

    if not driver_row:
        cursor.execute("SELECT name, phone, email, preferred_language FROM users WHERE id = ?", (user_id,))
        u_row = cursor.fetchone()
        u_name = u_row['name'] if u_row else 'Driver'
        u_phone = u_row['phone'] if u_row else ''
        u_email = u_row['email'] if u_row else ''
        
        new_driver_code = generate_unique_driver_id(conn)
        cursor.execute('''
            INSERT OR IGNORE INTO drivers (user_id, driver_id_code, name, phone, email, status)
            VALUES (?, ?, ?, ?, ?, 'ACTIVE')
        ''', (user_id, new_driver_code, u_name, u_phone, u_email))
        conn.commit()

        cursor.execute('''
            SELECT d.*, u.name as user_name, u.phone as user_phone, u.email as user_email, u.username
            FROM drivers d
            LEFT JOIN users u ON d.user_id = u.id
            WHERE d.user_id = ? OR u.id = ?
        ''', (user_id, user_id))
        driver_row = cursor.fetchone()

    driver = dict(driver_row) if driver_row else {}

    if driver and (not driver.get('driver_id_code') or not str(driver['driver_id_code']).startswith('DRV-')):
        raw_code = driver.get('driver_id_code', '') or ''
        digits = ''.join(c for c in str(raw_code) if c.isdigit())
        if digits:
            new_code = f"DRV-{int(digits):06d}"
        else:
            new_code = generate_unique_driver_id(conn)
        cursor.execute("UPDATE drivers SET driver_id_code = ? WHERE id = ?", (new_code, driver['id']))
        conn.commit()
        driver['driver_id_code'] = new_code

    if driver:
        session['driver_id_code'] = driver['driver_id_code']
        session['email'] = driver.get('email', '')
        session['name'] = driver.get('name', '')
        session['username'] = driver.get('username', '')

    # Fetch past emergency incident history with reports
    past_incidents = []
    if driver and driver.get('id'):
        cursor = conn.cursor()
        cursor.execute("""
            SELECT e.id, e.emergency_code, e.prediction, e.severity, e.status,
                   e.timestamp, e.driver_lat, e.driver_lng,
                   h.name as hospital_name,
                   mr.report_id_code, mr.pdf_filename,
                   mb.bill_id_code, mb.grand_total as bill_total
            FROM emergencies e
            LEFT JOIN hospitals h ON (COALESCE(e.accepted_hospital_id, e.hospital_id) = h.id)
            LEFT JOIN medical_reports mr ON e.id = mr.emergency_id
            LEFT JOIN medical_bills mb ON e.id = mb.emergency_id
            WHERE e.driver_id = ?
            ORDER BY e.id DESC LIMIT 10
        """, (driver['id'],))
        past_incidents = [dict(r) for r in cursor.fetchall()]

    conn.close()
    return render_template('driver_dashboard.html', driver=driver, past_incidents=past_incidents)



@main_bp.route('/dashboard/doctor')
def doctor_dashboard():
    """Doctor Portal Dashboard"""
    return render_template('doctor_dashboard.html')

@main_bp.route('/dashboard/nurse')
def nurse_dashboard():
    """Nurse Portal Dashboard"""
    return render_template('nurse_dashboard.html')

@main_bp.route('/dashboard/receptionist')
@hospital_required
def receptionist_dashboard():
    """Receptionist Portal Dashboard"""
    from database import get_db_connection
    hospital_id = session.get('hospital_id')
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get Hospital Name
    cursor.execute("SELECT name FROM hospitals WHERE id = ?", (hospital_id,))
    hosp_row = cursor.fetchone()
    hospital_name = hosp_row['name'] if hosp_row else 'Hospital'
    
    # Pagination params for admissions
    page = max(1, int(request.args.get('page', 1)))
    per_page = 10
    offset = (page - 1) * per_page

    # Total admissions count for pagination
    cursor.execute("SELECT COUNT(*) as cnt FROM hospital_admissions WHERE hospital_id = ?", (hospital_id,))
    total_admissions = cursor.fetchone()['cnt']
    total_pages = max(1, (total_admissions + per_page - 1) // per_page)

    # Staff count (receptionists at this hospital)
    cursor.execute("SELECT COUNT(*) as cnt FROM receptionists WHERE hospital_id = ? AND is_active = 1", (hospital_id,))
    staff_count = cursor.fetchone()['cnt']

    # Fetch paginated admissions with patient care data
    cursor.execute("""
        SELECT ha.*,
               d.driver_id_code, d.age, d.gender, d.blood_group,
               u.name as doctor_name,
               e.emergency_code, e.prediction as emg_prediction, e.severity as emg_severity,
               e.driver_lat, e.driver_lng,
               h2.latitude as hosp_lat, h2.longitude as hosp_lng,
               mb.grand_total as bill_total, mb.bill_id_code,
               mr.report_id_code, mr.pdf_filename
        FROM hospital_admissions ha
        LEFT JOIN drivers d ON ha.driver_id = d.id
        LEFT JOIN doctors doc ON ha.doctor_id = doc.id
        LEFT JOIN users u ON doc.user_id = u.id
        LEFT JOIN emergencies e ON ha.emergency_id = e.id
        LEFT JOIN hospitals h2 ON ha.hospital_id = h2.id
        LEFT JOIN medical_bills mb ON ha.emergency_id = mb.emergency_id
        LEFT JOIN medical_reports mr ON ha.emergency_id = mr.emergency_id
        WHERE ha.hospital_id = ?
        ORDER BY ha.admitted_at DESC
        LIMIT ? OFFSET ?
    """, (hospital_id, per_page, offset))
    admissions = [dict(r) for r in cursor.fetchall()]

    # Fetch medicines for each admission (from prescriptions)
    import json as _json
    medicines_map = {}
    for adm in admissions:
        if adm.get('emergency_id'):
            cursor.execute("SELECT medicines_json, diagnosis, treatment FROM prescriptions WHERE emergency_id = ? ORDER BY id DESC LIMIT 1", (adm['emergency_id'],))
            presc_row = cursor.fetchone()
            if presc_row:
                try:
                    meds = _json.loads(presc_row['medicines_json'] or '[]')
                except Exception:
                    meds = []
                medicines_map[adm['id']] = {
                    'medicines': meds,
                    'diagnosis': presc_row['diagnosis'],
                    'treatment': presc_row['treatment']
                }

    # Compute days in hospital per admission
    from datetime import datetime as _dt
    for adm in admissions:
        try:
            admitted = _dt.strptime(str(adm.get('admitted_at', ''))[:19], '%Y-%m-%d %H:%M:%S')
            discharged_at = adm.get('discharged_at')
            if discharged_at:
                discharged = _dt.strptime(str(discharged_at)[:19], '%Y-%m-%d %H:%M:%S')
            else:
                discharged = _dt.now()
            adm['days_in_hospital'] = max(1, (discharged - admitted).days)
        except Exception:
            adm['days_in_hospital'] = 1

    # Total bill amount for the page
    cursor.execute("SELECT COALESCE(SUM(mb.grand_total),0) as total FROM medical_bills mb JOIN hospital_admissions ha ON ha.emergency_id = mb.emergency_id WHERE ha.hospital_id = ?", (hospital_id,))
    total_bill = cursor.fetchone()['total']

    # Fetch active emergency dispatches matched to this hospital (real-time telemetry)
    cursor.execute("""
        SELECT e.id, e.emergency_code, e.prediction, e.severity, e.status,
               e.driver_lat, e.driver_lng, e.timestamp,
               d.driver_id_code, u.name as driver_name,
               h.name as hospital_name_col
        FROM emergencies e
        LEFT JOIN drivers d ON e.driver_id = d.id
        LEFT JOIN users u ON d.user_id = u.id
        LEFT JOIN hospitals h ON (COALESCE(e.accepted_hospital_id, e.hospital_id) = h.id)
        WHERE (e.hospital_id = ? OR e.accepted_hospital_id = ?)
          AND e.status NOT IN ('COMPLETED', 'RESOLVED', 'CANCELLED', 'DISCHARGED')
        ORDER BY e.id DESC
        LIMIT 103
    """, (hospital_id, hospital_id))
    active_emergencies = [dict(r) for r in cursor.fetchall()]

    conn.close()

    return render_template('receptionist_dashboard.html',
                           admissions=admissions,
                           hospital_name=hospital_name,
                           hospital_id=hospital_id,
                           active_emergencies=active_emergencies,
                           staff_count=staff_count,
                           total_admissions=total_admissions,
                           total_pages=total_pages,
                           current_page=page,
                           total_bill=total_bill,
                           medicines_map=medicines_map)

@main_bp.route('/dashboard/pharmacist')
def pharmacist_dashboard():
    """Pharmacist Portal Dashboard"""
    return render_template('pharmacist_dashboard.html')

@main_bp.route('/dashboard/admin')
@admin_required
def admin_dashboard():
    from database import get_db_connection
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM drivers")
    total_drivers = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM hospitals")
    total_hospitals = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM ambulances")
    total_ambulances = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM family_members")
    total_families = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM emergencies WHERE UPPER(status) NOT IN ('COMPLETED', 'RESOLVED', 'CANCELLED', 'CLOSED')")
    active_emergencies = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM emergencies")
    total_emergencies = cursor.fetchone()[0]

    conn.close()

    return render_template(
        'admin_dashboard.html',
        total_drivers=total_drivers,
        total_hospitals=total_hospitals,
        total_ambulances=total_ambulances,
        total_families=total_families,
        active_emergencies=active_emergencies,
        total_emergencies=total_emergencies
    )

@main_bp.route('/hospital/dashboard', endpoint='hospital_dashboard_alias')
@main_bp.route('/dashboard/hospital', endpoint='hospital_dashboard')
@hospital_required
def hospital_dashboard():
    from database import get_db_connection
    hospital_id = session.get('hospital_id')
    if not hospital_id:
        return redirect(url_for('auth.hospital_login'))

    conn = get_db_connection()
    cursor = conn.cursor()

    # Fetch Hospital Record
    cursor.execute("SELECT * FROM hospitals WHERE id = ?", (hospital_id,))
    hosp_row = cursor.fetchone()
    if not hosp_row:
        conn.close()
        return redirect(url_for('auth.hospital_login'))

    hospital = dict(hosp_row)

    # Fetch Patients (Patients & Hospital Admissions)
    cursor.execute("SELECT * FROM patients WHERE hospital_id = ?", (hospital_id,))
    pts = [dict(r) for r in cursor.fetchall()]
    cursor.execute("SELECT * FROM hospital_admissions WHERE hospital_id = ?", (hospital_id,))
    admissions = [dict(r) for r in cursor.fetchall()]

    # Fetch Emergencies
    cursor.execute("""
        SELECT e.*, u.name as driver_name, u.phone as driver_phone
        FROM emergencies e
        LEFT JOIN drivers d ON e.driver_id = d.id
        LEFT JOIN users u ON d.user_id = u.id
        WHERE e.hospital_id = ? OR e.accepted_hospital_id = ? 
           OR e.id IN (SELECT emergency_id FROM hospital_emergency_requests WHERE hospital_id = ?)
           OR UPPER(e.status) NOT IN ('COMPLETED', 'RESOLVED', 'CANCELLED', 'RESOLVED_COMPLETED', 'CLOSED')
        ORDER BY e.id DESC
    """, (hospital_id, hospital_id, hospital_id))
    emergencies_raw = [dict(r) for r in cursor.fetchall()]


    if not emergencies_raw:
        # emergency_events table may not exist — keep empty list, no fallback needed
        pass

    active_emergencies = []
    all_emergencies = []
    for e in emergencies_raw:
        item = {
            "id": e['id'],
            "driver_id": e.get('driver_id', '101'),
            "driver_id_code": f"DRV-{e.get('driver_id', 1):06d}",
            "driver_name": e.get('driver_name') or f"Driver #{e.get('driver_id', 101)}",
            "prediction": e.get('prediction') or e.get('emergency_type') or "Emergency Alert",
            "severity": e.get('severity') or e.get('risk_level') or "HIGH",
            "status": e.get('status') or "ACTIVE",
            "timestamp": str(e.get('timestamp') or e.get('created_at') or "Just Now"),
            "location": f"Lat: {e.get('driver_lat', 11.3410):.4f}, Lng: {e.get('driver_lng', 77.7170):.4f}" if e.get('driver_lat') else "Erode"
        }
        all_emergencies.append(item)
        if (e.get('status') or '').upper() not in ['RESOLVED', 'CANCELLED', 'COMPLETED', 'CLOSED']:
            active_emergencies.append(item)


    # Fetch Doctors
    cursor.execute("SELECT * FROM doctors WHERE hospital_id = ?", (hospital_id,))
    doctors = [dict(r) for r in cursor.fetchall()]

    # Fetch Nurses
    cursor.execute("SELECT * FROM nurses WHERE hospital_id = ?", (hospital_id,))
    nurses = [dict(r) for r in cursor.fetchall()]

    # Fetch Receptionists
    cursor.execute("SELECT * FROM receptionists WHERE hospital_id = ?", (hospital_id,))
    receptionists = [dict(r) for r in cursor.fetchall()]

    # Fetch Pharmacists
    cursor.execute("SELECT * FROM pharmacists WHERE hospital_id = ?", (hospital_id,))
    pharmacists = [dict(r) for r in cursor.fetchall()]

    # Fetch Ambulances
    cursor.execute("SELECT * FROM ambulances WHERE hospital_id = ?", (hospital_id,))
    ambulances = [dict(r) for r in cursor.fetchall()]

    # Fetch Beds
    cursor.execute("SELECT * FROM beds WHERE hospital_id = ?", (hospital_id,))
    beds = [dict(r) for r in cursor.fetchall()]

    avail_beds = hospital.get('available_beds') if hospital.get('available_beds') is not None else 10
    icu_beds = hospital.get('icu_beds') if hospital.get('icu_beds') is not None else 5
    if beds:
        avail_beds = sum(1 for b in beds if b.get('status') == 'Available')
        icu_beds = sum(1 for b in beds if b.get('type') == 'ICU' and b.get('status') == 'Available')

    conn.close()

    total_patients_count = len(pts) + len(admissions)
    total_staff_count = len(doctors) + len(nurses) + len(receptionists) + len(pharmacists)

    staff_counts = {
        'doctors': len(doctors),
        'nurses': len(nurses),
        'receptionists': len(receptionists),
        'pharmacists': len(pharmacists),
        'total': total_staff_count
    }

    metrics = {
        'total_patients': total_patients_count,
        'active_emergencies': len(active_emergencies),
        'available_beds': avail_beds,
        'icu_beds': icu_beds,
        'doctors_count': len(doctors),
        'nurses_count': len(nurses),
        'ambulances_count': len(ambulances)
    }

    return render_template(
        'hospital_dashboard.html',
        hospital=hospital,
        metrics=metrics,
        active_emergencies=active_emergencies,
        all_emergencies=all_emergencies,
        doctors=doctors,
        nurses=nurses,
        receptionists=receptionists,
        pharmacists=pharmacists,
        ambulances=ambulances,
        patients=pts,
        staff_counts=staff_counts,
        sub_role=session.get('role')
    )

@main_bp.route('/dashboard/logistics')
def logistics_dashboard():
    return render_template('logistics_dashboard.html')

@main_bp.route('/dashboard/ambulance')
@login_required
def ambulance_dashboard():
    from database import get_db_connection
    user_id = session.get('user_id')
    conn = get_db_connection()
    cursor = conn.cursor()

    amb = None
    if user_id:
        # Try driver_user_id first (new records), then user_id (legacy column)
        cursor.execute("SELECT * FROM ambulances WHERE driver_user_id = ?", (user_id,))
        amb_row = cursor.fetchone()
        if not amb_row:
            cursor.execute("SELECT * FROM ambulances WHERE user_id = ?", (user_id,))
            amb_row = cursor.fetchone()
        if amb_row:
            amb = dict(amb_row)

    active_emergencies = []
    if amb:
        cursor.execute("""
            SELECT e.*, d.driver_id_code, u.name as driver_name, u.phone as driver_phone,
                   d.age, d.gender, d.blood_group,
                   h.name as hospital_name, h.address as hosp_address,
                   h.emergency_number as hosp_phone, h.latitude as hosp_lat, h.longitude as hosp_lng
            FROM emergencies e
            JOIN drivers d ON e.driver_id = d.id
            JOIN users u ON d.user_id = u.id
            LEFT JOIN hospitals h ON (COALESCE(e.accepted_hospital_id, e.hospital_id) = h.id)
            WHERE UPPER(e.status) NOT IN ('COMPLETED', 'RESOLVED', 'CANCELLED', 'RESOLVED_COMPLETED', 'CLOSED')
              AND (
                  e.ambulance_id = ? 
                  OR e.accepted_ambulance_id = ?
                  OR e.id IN (SELECT emergency_id FROM ambulance_requests WHERE ambulance_id = ?)
                  OR (e.accepted_ambulance_id IS NULL AND UPPER(e.status) IN ('ACTIVE', 'DISPATCHING', 'AMBULANCE_REQUESTED', 'AMBULANCE_SEARCHING', 'REQUESTED', 'PENDING'))
              )
            ORDER BY e.id DESC
        """, (amb['id'], amb['id'], amb['id']))
        rows = cursor.fetchall()
        active_emergencies = [dict(r) for r in rows]

        if not active_emergencies:
            cursor.execute("""
                SELECT e.*, d.driver_id_code, u.name as driver_name, u.phone as driver_phone,
                       d.age, d.gender, d.blood_group,
                       h.name as hospital_name, h.address as hosp_address,
                       h.emergency_number as hosp_phone, h.latitude as hosp_lat, h.longitude as hosp_lng
                FROM emergencies e
                JOIN drivers d ON e.driver_id = d.id
                JOIN users u ON d.user_id = u.id
                LEFT JOIN hospitals h ON (COALESCE(e.accepted_hospital_id, e.hospital_id) = h.id)
                WHERE UPPER(e.status) NOT IN ('COMPLETED', 'RESOLVED', 'CANCELLED', 'RESOLVED_COMPLETED', 'CLOSED')
                ORDER BY e.id DESC
            """)
            active_emergencies = [dict(r) for r in cursor.fetchall()]

    elif session.get('role') == 'admin':
        cursor.execute("""
            SELECT e.*, d.driver_id_code, u.name as driver_name, u.phone as driver_phone,
                   d.age, d.gender, d.blood_group,
                   h.name as hospital_name, h.address as hosp_address,
                   h.emergency_number as hosp_phone, h.latitude as hosp_lat, h.longitude as hosp_lng
            FROM emergencies e
            JOIN drivers d ON e.driver_id = d.id
            JOIN users u ON d.user_id = u.id
            LEFT JOIN hospitals h ON (COALESCE(e.accepted_hospital_id, e.hospital_id) = h.id)
            WHERE UPPER(e.status) NOT IN ('COMPLETED', 'RESOLVED', 'CANCELLED', 'RESOLVED_COMPLETED', 'CLOSED')
            ORDER BY e.id DESC
        """)
        rows = cursor.fetchall()
        active_emergencies = [dict(r) for r in rows]

    for em in active_emergencies:
        cursor.execute("SELECT step, detail, status, timestamp FROM emergency_timeline WHERE emergency_id = ? ORDER BY id ASC", (em['id'],))
        em['timeline'] = [dict(t) for t in cursor.fetchall()]

    history = []
    if amb:
        cursor.execute("""
            SELECT e.*, u.name as driver_name, e.status, e.prediction, e.timestamp
            FROM emergencies e
            JOIN drivers d ON e.driver_id = d.id
            JOIN users u ON d.user_id = u.id
            WHERE (e.ambulance_id = ? OR e.accepted_ambulance_id = ?) 
              AND UPPER(e.status) IN ('COMPLETED', 'RESOLVED', 'CANCELLED', 'RESOLVED_COMPLETED')
            ORDER BY e.id DESC
        """, (amb['id'], amb['id']))
        history = [dict(r) for r in cursor.fetchall()]

    conn.close()


    return render_template('ambulance_dashboard.html',
                           ambulance=amb,
                           active_emergencies=active_emergencies,
                           history=history,
                           my_amb_id=amb['id'] if amb else None)

@main_bp.route('/dashboard/family')
@login_required
def family_dashboard():
    from database import get_db_connection
    user_id = session.get('user_id')
    if not user_id or session.get('role') != 'family':
        flash("Family authentication required.", "danger")
        return redirect(url_for('auth.family_login'))

    conn = get_db_connection()
    cursor = conn.cursor()

    # Fetch family member profile for logged in user
    cursor.execute("SELECT * FROM family_members WHERE user_id = ?", (user_id,))
    family_row = cursor.fetchone()
    if not family_row:
        conn.close()
        flash("Family profile record not found.", "warning")
        return render_template('family_dashboard.html', family=None, driver=None, emergency=None)

    family = dict(family_row)
    driver_db_id = family.get('driver_id')
    driver_code = family.get('driver_id_code')

    # Fetch the exact linked driver from database
    cursor.execute('''
        SELECT d.*, u.name, u.phone, u.email
        FROM drivers d
        JOIN users u ON d.user_id = u.id
        WHERE d.id = ? OR d.driver_id_code = ?
    ''', (driver_db_id, driver_code))
    driver_row = cursor.fetchone()
    driver = dict(driver_row) if driver_row else None

    # Fetch active emergency for linked driver — prefer HOSPITAL_ACCEPTED status (patient already admitted)
    active_emergency = None
    timeline = []
    if driver:
        # First try: most recent HOSPITAL_ACCEPTED emergency (loved one confirmed at hospital)
        cursor.execute('''
            SELECT e.*, h.name as hospital_name, h.address as hospital_address, h.emergency_number as hospital_phone,
                   h.latitude as hosp_lat, h.longitude as hosp_lng,
                   a.driver_name as ambulance_driver_name, a.vehicle_number as ambulance_vehicle_number, a.driver_phone as ambulance_driver_phone
            FROM emergencies e
            LEFT JOIN hospitals h ON (COALESCE(e.accepted_hospital_id, e.hospital_id) = h.id)
            LEFT JOIN ambulances a ON (COALESCE(e.accepted_ambulance_id, e.ambulance_id) = a.id)
            WHERE e.driver_id = ?
              AND UPPER(e.status) IN ('HOSPITAL_ACCEPTED', 'AMBULANCE_DISPATCHED', 'EN_ROUTE_TO_PATIENT',
                                      'ARRIVED_AT_PATIENT', 'PATIENT_PICKED_UP', 'ARRIVED_AT_HOSPITAL', 'TREATED')
            ORDER BY e.id DESC LIMIT 1
        ''', (driver['id'],))
        em_row = cursor.fetchone()

        # Fallback: any latest emergency if nothing accepted yet
        if not em_row:
            cursor.execute('''
                SELECT e.*, h.name as hospital_name, h.address as hospital_address, h.emergency_number as hospital_phone,
                       h.latitude as hosp_lat, h.longitude as hosp_lng,
                       a.driver_name as ambulance_driver_name, a.vehicle_number as ambulance_vehicle_number, a.driver_phone as ambulance_driver_phone
                FROM emergencies e
                LEFT JOIN hospitals h ON (COALESCE(e.accepted_hospital_id, e.hospital_id) = h.id)
                LEFT JOIN ambulances a ON (COALESCE(e.accepted_ambulance_id, e.ambulance_id) = a.id)
                WHERE e.driver_id = ?
                  AND UPPER(e.status) NOT IN ('COMPLETED', 'RESOLVED', 'CANCELLED', 'DISCHARGED')
                ORDER BY e.id DESC LIMIT 1
            ''', (driver['id'],))
            em_row = cursor.fetchone()

        if em_row:
            active_emergency = dict(em_row)
            cursor.execute("SELECT step, detail, status, timestamp FROM emergency_timeline WHERE emergency_id = ? ORDER BY id ASC", (active_emergency['id'],))
            timeline = [dict(t) for t in cursor.fetchall()]

    # Fetch health vitals log
    health_log = None
    if driver:
        cursor.execute("SELECT * FROM health_logs WHERE driver_id = ? ORDER BY timestamp DESC LIMIT 1", (driver['id'],))
        hl_row = cursor.fetchone()
        if hl_row:
            health_log = dict(hl_row)

    # Fetch past emergency incidents history
    incident_history = []
    if driver:
        cursor.execute('''
            SELECT e.*, h.name as hospital_name, r.report_id_code
            FROM emergencies e
            LEFT JOIN hospitals h ON (COALESCE(e.accepted_hospital_id, e.hospital_id) = h.id)
            LEFT JOIN medical_reports r ON e.id = r.emergency_id
            WHERE e.driver_id = ?
            ORDER BY e.id DESC LIMIT 6
        ''', (driver['id'],))
        incident_history = [dict(r) for r in cursor.fetchall()]

    conn.close()

    return render_template(
        'family_dashboard.html',
        family=family,
        driver=driver,
        emergency=active_emergency,
        health_log=health_log,
        timeline=timeline,
        incident_history=incident_history
    )


@main_bp.route('/billing/<bill_id_code>')
def view_medical_bill(bill_id_code):
    from database import get_db_connection
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT b.*, p.patient_id_code, h.name as hospital_name
        FROM medical_bills b
        JOIN patients p ON b.patient_id = p.id
        JOIN hospitals h ON b.hospital_id = h.id
        WHERE b.bill_id_code = ? OR b.id = ?
    """, (bill_id_code, bill_id_code))
    bill_row = cursor.fetchone()

    if not bill_row:
        conn.close()
        return "Medical Bill Not Found", 404

    bill = dict(bill_row)
    cursor.execute("SELECT * FROM bill_items WHERE bill_id = ?", (bill['id'],))
    items = [dict(r) for r in cursor.fetchall()]
    conn.close()

    return render_template('billing.html', bill=bill, items=items)

LANG_NAMES = {'en-US': 'English', 'hi-IN': 'Hindi', 'ta-IN': 'Tamil', 'te-IN': 'Telugu', 'bn-IN': 'Bengali', 'ml-IN': 'Malayalam', 'mr-IN': 'Marathi', 'gu-IN': 'Gujarati', 'kn-IN': 'Kannada'}

@main_bp.route('/register', methods=['GET', 'POST'])
def register_page():
    if request.method == 'POST':
        try:
            from database import get_db_connection, generate_unique_driver_id
            from werkzeug.security import generate_password_hash
            data = request.form
            
            username = data.get('username')
            password = data.get('password')
            name = data.get('name')
            phone = data.get('phone')
            email = data.get('email', '')
            age = data.get('age', 28)
            gender = data.get('gender', 'Male')
            blood_group = data.get('blood_group', 'O+')
            preferred_language = data.get('preferred_language', 'en-US')
            
            if not username or not password or not name or not phone:
                return render_template('register.html', error="Name, Phone, Username, and Password are required.", lang_names=LANG_NAMES)
                
            conn = get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
            if cursor.fetchone():
                conn.close()
                return render_template('register.html', error=f"Username '{username}' already exists.", lang_names=LANG_NAMES)
                
            # Generate unique Driver ID (Format: DRV-000001)
            driver_code = generate_unique_driver_id(conn)

            hashed_pw = generate_password_hash(password, method='pbkdf2:sha256')
            cursor.execute('''
                INSERT INTO users (username, password, role, name, phone, email)
                VALUES (?, ?, 'driver', ?, ?, ?)
            ''', (username, hashed_pw, name, phone, email))
            user_id = cursor.lastrowid
            
            # Create Driver profile record
            cursor.execute('''
                INSERT INTO drivers (
                    user_id, driver_id_code, name, phone, email, age, gender, blood_group,
                    preferred_language, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'ACTIVE')
            ''', (user_id, driver_code, name, phone, email, age, gender, blood_group, preferred_language))
            driver_db_id = cursor.lastrowid

            # Log audit
            cursor.execute('''
                INSERT INTO audit_logs (user_id, username, action, details)
                VALUES (?, ?, 'DRIVER_REGISTERED', ?)
            ''', (user_id, username, f"Registered Driver {name} ({driver_code})"))

            conn.commit()
            conn.close()
            
            flash(f"Driver Registration Successful! ID: {driver_code} — {name}. Please login.", "success")
            return redirect(url_for('auth.login', role='driver'))
            
        except Exception as e:
            return render_template('register.html', error=f"Registration failed: {str(e)}", lang_names=LANG_NAMES)
            
    return render_template('register.html', lang_names=LANG_NAMES)

@main_bp.route('/register/staff')
@hospital_required
def register_staff_page():
    return render_template('register_staff.html')

@main_bp.route('/register/ambulance', methods=['GET', 'POST'])
def register_ambulance_page():
    if request.method == 'POST':
        try:
            from database import get_db_connection
            from werkzeug.security import generate_password_hash
            data = request.form
            username = data.get('username')
            password = data.get('password')
            name = data.get('name')
            phone = data.get('phone')
            vehicle_number = data.get('vehicle_number')
            hospital_id = session.get('hospital_id', 1)
            
            if not username or not password or not name:
                return render_template('register_ambulance.html', error="Missing required fields", lang_names=LANG_NAMES)
                
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
            if cursor.fetchone():
                conn.close()
                return render_template('register_ambulance.html', error="Username already exists", lang_names=LANG_NAMES)
                
            hashed_pw = generate_password_hash(password)
            cursor.execute('''
                INSERT INTO users (username, password, role, name, phone, hospital_id)
                VALUES (?, ?, 'ambulance', ?, ?, ?)
            ''', (username, hashed_pw, name, phone, hospital_id))
            user_id = cursor.lastrowid
            
            emergency_call_consent = 1 if data.get('emergency_call_consent') == 'on' else 0
            preferred_language = data.get('preferred_language', 'en')
            address = data.get('address', 'Perundurai, Tamil Nadu')
            phone_verified = 1
            
            from geocoding_service import geocode_address
            lat, lng = geocode_address(address)
            
            from database import generate_unique_ambulance_id
            hosp_code = None
            if hospital_id:
                cursor.execute("SELECT hospital_id_code FROM hospitals WHERE id = ?", (hospital_id,))
                h_row = cursor.fetchone()
                if h_row: hosp_code = h_row['hospital_id_code']
            
            amb_code = generate_unique_ambulance_id(
                is_private=(not hospital_id),
                hospital_id_code=hosp_code,
                city=address,
                conn=conn
            )
            final_vehicle_no = vehicle_number if vehicle_number and vehicle_number.strip() else amb_code

            cursor.execute('''
                INSERT INTO ambulances (hospital_id, vehicle_number, driver_name, driver_phone, status, driver_user_id, emergency_call_consent, emergency_call_enabled, preferred_language, phone_verified, consent_timestamp, latitude, longitude, ambulance_driver_id_code)
                VALUES (?, ?, ?, ?, 'Available', ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, ?, ?, ?)
            ''', (hospital_id, final_vehicle_no, name, phone, user_id, emergency_call_consent, emergency_call_consent, preferred_language, phone_verified, lat, lng, amb_code))


            
            # Log consent audit
            cursor.execute('''
                INSERT INTO consent_audit_logs (entity_id, entity_type, consent_type, new_value, changed_by, reason)
                VALUES (?, 'Ambulance', 'Emergency Calls', ?, ?, 'Initial Registration')
            ''', (cursor.lastrowid, 'TRUE' if emergency_call_consent else 'FALSE', username))
            
            conn.commit()
            conn.close()
            flash("Ambulance Driver Registered Successfully!", "success")
            return redirect(url_for('auth.ambulance_login'))
        except Exception as e:
            return render_template('register_ambulance.html', error=f"Registration failed: {str(e)}", lang_names=LANG_NAMES)

    return render_template('register_ambulance.html', lang_names=LANG_NAMES)

@main_bp.route('/register/family', methods=['GET', 'POST'])
def register_family_page():
    if request.method == 'POST':
        try:
            from database import get_db_connection, generate_unique_family_id, verify_driver_id_exists
            from werkzeug.security import generate_password_hash
            data = request.form
            username = data.get('username')
            password = data.get('password')
            name = data.get('name')
            phone = data.get('phone')
            email = data.get('email', '')
            relation = data.get('relation', 'Family')
            driver_id_input = data.get('driver_id', '').strip()
            
            if not username or not password or not name or not phone or not driver_id_input:
                return render_template('register_family.html', error="Name, Phone, Driver ID, Username, and Password are required.", lang_names=LANG_NAMES)
                
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # 1. Validate username uniqueness
            cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
            if cursor.fetchone():
                conn.close()
                return render_template('register_family.html', error=f"Username '{username}' already exists.", lang_names=LANG_NAMES)

            # 2. Verify driver existence & retrieve DB driver_id and canonical driver_id_code
            driver_info = verify_driver_id_exists(driver_id_input)
            if not driver_info:
                conn.close()
                return render_template('register_family.html', error=f"Driver with ID '{driver_id_input}' not found. Please verify Driver ID.", lang_names=LANG_NAMES)

            driver_db_id = driver_info['id']
            canonical_driver_code = driver_info['driver_id_code']
            driver_name = driver_info['name']

            # 3. Generate unique Family ID (Format: FAM-000001)
            family_code = generate_unique_family_id(conn)

            # 4. Create User Account for Family Member
            hashed_pw = generate_password_hash(password, method='pbkdf2:sha256')
            cursor.execute('''
                INSERT INTO users (username, password, role, name, phone, email)
                VALUES (?, ?, 'family', ?, ?, ?)
            ''', (username, hashed_pw, name, phone, email))
            user_id = cursor.lastrowid

            emergency_sms_consent = 1 if data.get('emergency_sms_consent') == 'on' else 0
            emergency_status_consent = 1 if data.get('emergency_status_consent') == 'on' else 0
            notification_enabled = emergency_sms_consent
            
            # Check if phone is verified
            cursor.execute("SELECT is_verified FROM otp_verifications WHERE phone = ? AND purpose = 'family_reg' ORDER BY id DESC LIMIT 1", (phone,))
            otp_record = cursor.fetchone()
            phone_verified = 1


            # 5. Create Family Member Profile Record & Link Driver
            cursor.execute('''
                INSERT INTO family_members (
                    user_id, driver_id, family_id_code, name, phone, email, relation, driver_id_code, status,
                    emergency_sms_consent, emergency_status_consent, notification_enabled, phone_verified, consent_timestamp
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'ACTIVE', ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ''', (user_id, driver_db_id, family_code, name, phone, email, relation, canonical_driver_code,
                  emergency_sms_consent, emergency_status_consent, notification_enabled, phone_verified))
            family_db_id = cursor.lastrowid

            # Log consent audit
            cursor.execute('''
                INSERT INTO consent_audit_logs (entity_id, entity_type, consent_type, new_value, changed_by, reason)
                VALUES (?, 'Family', 'Emergency SMS', ?, ?, 'Initial Registration')
            ''', (family_db_id, 'TRUE' if emergency_sms_consent else 'FALSE', username))

            # 6. Log Audit Trail
            cursor.execute('''
                INSERT INTO audit_logs (user_id, username, action, details)
                VALUES (?, ?, 'FAMILY_REGISTERED', ?)
            ''', (user_id, username, f"Registered Family member {name} ({family_code}) linked to Driver {driver_name} ({canonical_driver_code})"))

            conn.commit()
            conn.close()

            flash(f"Family Member Registered Successfully! ID: {family_code} linked to Driver {driver_name} ({canonical_driver_code}). Please login.", "success")
            return redirect(url_for('auth.login', role='family'))

        except Exception as e:
            return render_template('register_family.html', error=f"Registration failed: {str(e)}", lang_names=LANG_NAMES)

    return render_template('register_family.html', lang_names=LANG_NAMES)


@main_bp.route('/dashboard/patient/report/<int:admission_id>')
@hospital_required
def patient_report(admission_id):
    from models import HospitalAdmission, HealthReading, EmergencyEvent, User, HospitalStaff
    admission = HospitalAdmission.query.get_or_404(admission_id)
    
    # Ensure authorization
    if session.get('role') != 'admin' and admission.hospital_id != session.get('hospital_id'):
        return "Unauthorized", 403
        
    emergency = None
    vitals = None
    
    if admission.emergency_id:
        emergency = EmergencyEvent.query.get(admission.emergency_id)
        
    if admission.driver_id:
        vitals = HealthReading.query.filter_by(driver_id=admission.driver_id).order_by(HealthReading.timestamp.desc()).first()
        
    doctor_name = "Unassigned"
    if admission.doctor_id:
        doc = HospitalStaff.query.get(admission.doctor_id)
        if doc:
            doc_user = User.query.get(doc.user_id)
            if doc_user:
                doctor_name = doc_user.name
                
    nurse_name = "Unassigned"
    if admission.nurse_id:
        nurse = HospitalStaff.query.get(admission.nurse_id)
        if nurse:
            nurse_user = User.query.get(nurse.user_id)
            if nurse_user:
                nurse_name = nurse_user.name

    from datetime import datetime
    return render_template('patient_report.html',
        admission=admission,
        emergency=emergency,
        vitals=vitals,
        doctor_name=doctor_name,
        nurse_name=nurse_name,
        now=datetime.utcnow()
    )
