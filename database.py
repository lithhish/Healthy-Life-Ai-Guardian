import sqlite3
import os

DATABASE_PATH = os.path.join(os.path.dirname(__file__), 'guardian.db')

def get_db_connection():
    conn = sqlite3.connect(DATABASE_PATH, timeout=30.0)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute('PRAGMA journal_mode=WAL;')
        conn.execute('PRAGMA busy_timeout=30000;')
    except Exception:
        pass
    return conn



def normalize_driver_id(input_str):
    if not input_str:
        return ""
    clean = str(input_str).strip().upper()
    digits = ''.join(c for c in clean if c.isdigit())
    if digits:
        try:
            return f"DRV-{int(digits):06d}"
        except ValueError:
            pass
    return clean.replace(' ', '')


def _get_place_code(city_or_address: str) -> str:
    if not city_or_address:
        return "ERD"
    clean = ''.join(c.upper() for c in str(city_or_address) if c.isalnum())
    if len(clean) >= 3:
        return clean[:3]
    elif len(clean) > 0:
        return clean.ljust(3, 'X')
    return "ERD"


def _get_hospital_num(hospital_id_or_code) -> str:
    if not hospital_id_or_code:
        return "000001"
    digits = ''.join(c for c in str(hospital_id_or_code) if c.isdigit())
    if digits:
        try:
            return f"{int(digits):06d}"
        except ValueError:
            pass
    return "000001"


def _find_lowest_available_id(conn, prefix: str, table_name: str, column_name: str) -> str:
    cursor = conn.cursor()
    cursor.execute(f"SELECT {column_name} FROM {table_name} WHERE {column_name} LIKE ?", (f"{prefix}%",))
    rows = cursor.fetchall()
    
    used = set()
    for r in rows:
        val = r[column_name]
        if val:
            val_str = str(val)
            suffix = val_str[len(prefix):] if val_str.startswith(prefix) else val_str
            digits = ''.join(c for c in suffix if c.isdigit())
            if digits:
                try:
                    used.add(int(digits))
                except ValueError:
                    pass
    
    num = 1
    while num in used:
        num += 1
        
    return f"{prefix}{num:06d}"


def _generate_monotonic_id(conn, entity_name, prefix, table_name, column_name):
    return _find_lowest_available_id(conn, f"{prefix}-", table_name, column_name)


def generate_unique_driver_id(conn=None):
    close_conn = False
    if conn is None:
        conn = get_db_connection()
        close_conn = True

    code = _find_lowest_available_id(conn, "DRV-", "drivers", "driver_id_code")
    if close_conn:
        conn.commit()
        conn.close()
    return code


def generate_unique_hospital_id(city="Erode", conn=None):
    close_conn = False
    if conn is None:
        conn = get_db_connection()
        close_conn = True

    place_code = _get_place_code(city)
    prefix = f"HOS-{place_code}-"
    code = _find_lowest_available_id(conn, prefix, "hospitals", "hospital_id_code")
    if close_conn:
        conn.commit()
        conn.close()
    return code


def generate_unique_family_id(conn=None):
    close_conn = False
    if conn is None:
        conn = get_db_connection()
        close_conn = True

    code = _find_lowest_available_id(conn, "FAM-", "family_members", "family_id_code")
    if close_conn:
        conn.commit()
        conn.close()
    return code


def generate_unique_ambulance_id(is_private=True, hospital_id_code=None, city="Erode", conn=None, prefix=None):
    close_conn = False
    if conn is None:
        conn = get_db_connection()
        close_conn = True

    cursor = conn.cursor()
    try:
        cursor.execute("ALTER TABLE ambulances ADD COLUMN ambulance_driver_id_code TEXT")
    except Exception:
        pass

    if prefix:
        use_prefix = prefix
    elif is_private or not hospital_id_code:
        use_prefix = "AMB-"
    else:
        hosp_num = _get_hospital_num(hospital_id_code)
        use_prefix = f"AMB-{hosp_num}-"

    code = _find_lowest_available_id(conn, use_prefix, "ambulances", "ambulance_driver_id_code")
    if close_conn:
        conn.commit()
        conn.close()
    return code



def generate_unique_emergency_id(conn=None):
    close_conn = False
    if conn is None:
        conn = get_db_connection()
        close_conn = True

    code = _find_lowest_available_id(conn, "EMG-", "emergencies", "emergency_code")
    if close_conn:
        conn.commit()
        conn.close()
    return code


def generate_unique_ambulance_request_id(conn=None):
    close_conn = False
    if conn is None:
        conn = get_db_connection()
        close_conn = True

    code = _find_lowest_available_id(conn, "REQ-", "ambulance_requests", "request_id_code")
    if close_conn:
        conn.commit()
        conn.close()
    return code


def generate_unique_report_id(conn=None):
    close_conn = False
    if conn is None:
        conn = get_db_connection()
        close_conn = True

    code = _find_lowest_available_id(conn, "RPT-", "medical_reports", "report_id_code")
    if close_conn:
        conn.commit()
        conn.close()
    return code


def generate_unique_staff_id(sub_role, hospital_id_code=None, conn=None):
    close_conn = False
    if conn is None:
        conn = get_db_connection()
        close_conn = True

    hosp_num = _get_hospital_num(hospital_id_code)
    prefix_code = 'STA'
    sub_lower = str(sub_role).lower()
    if sub_lower in ['doctor', 'doc']:
        prefix_code = 'DOC'
    elif sub_lower in ['nurse', 'nur']:
        prefix_code = 'NUR'
    elif sub_lower in ['pharmacy', 'pharmacist', 'pha']:
        prefix_code = 'PHA'
    elif sub_lower in ['reception', 'receptionist', 'rec']:
        prefix_code = 'REP'
    elif sub_lower in ['hospital_management', 'management', 'mgt']:
        prefix_code = 'MGT'

    prefix = f"{prefix_code}-{hosp_num}-"
    staff_id_code = _find_lowest_available_id(conn, prefix, "hospital_staff", "staff_id_code")
    if close_conn:
        conn.commit()
        conn.close()
    return staff_id_code



def generate_unique_patient_id(conn=None):
    close_conn = False
    if conn is None:
        conn = get_db_connection()
        close_conn = True

    cursor = conn.cursor()
    cursor.execute("SELECT patient_id_code FROM patients WHERE patient_id_code LIKE 'PAT%' ORDER BY id DESC LIMIT 1")
    row = cursor.fetchone()
    next_num = 1

    if row and row['patient_id_code']:
        val = row['patient_id_code'].replace('PAT-', '').replace('PAT', '')
        try:
            next_num = int(val) + 1
        except ValueError:
            next_num = 1

    patient_id_code = f"PAT-{next_num:06d}"
    if close_conn:
        conn.close()
    return patient_id_code


def generate_unique_emergency_id(conn=None):
    close_conn = False
    if conn is None:
        conn = get_db_connection()
        close_conn = True

    cursor = conn.cursor()
    cursor.execute("SELECT emergency_code FROM emergencies WHERE emergency_code LIKE 'EMG%' ORDER BY id DESC LIMIT 1")
    row = cursor.fetchone()
    next_num = 1

    if row and row['emergency_code']:
        val = row['emergency_code'].replace('EMG-', '').replace('EMG', '')
        try:
            next_num = int(val) + 1
        except ValueError:
            next_num = 1

    emergency_code = f"EMG-{next_num:06d}"
    if close_conn:
        conn.close()
    return emergency_code


def generate_unique_report_id(conn=None):
    close_conn = False
    if conn is None:
        conn = get_db_connection()
        close_conn = True

    cursor = conn.cursor()
    cursor.execute("SELECT report_id_code FROM medical_reports WHERE report_id_code LIKE 'REP%' ORDER BY id DESC LIMIT 1")
    row = cursor.fetchone()
    next_num = 1

    if row and row['report_id_code']:
        val = row['report_id_code'].replace('REP-', '').replace('REP', '')
        try:
            next_num = int(val) + 1
        except ValueError:
            next_num = 1

    report_id_code = f"REP-{next_num:06d}"
    if close_conn:
        conn.close()
    return report_id_code


def generate_unique_bill_id(conn=None):
    close_conn = False
    if conn is None:
        conn = get_db_connection()
        close_conn = True

    cursor = conn.cursor()
    cursor.execute("SELECT bill_id_code FROM medical_bills WHERE bill_id_code LIKE 'BILL%' ORDER BY id DESC LIMIT 1")
    row = cursor.fetchone()
    next_num = 1

    if row and row['bill_id_code']:
        val = row['bill_id_code'].replace('BILL-', '').replace('BILL', '')
        try:
            next_num = int(val) + 1
        except ValueError:
            next_num = 1

    bill_id_code = f"BILL-{next_num:06d}"
    if close_conn:
        conn.close()
    return bill_id_code


def verify_driver_id_exists(driver_id_code):
    if not driver_id_code:
        return None
    
    norm_code = normalize_driver_id(driver_id_code)
    raw_code = str(driver_id_code).strip().upper()
    no_hyphen = norm_code.replace('-', '')
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT d.id, d.driver_id_code, COALESCE(d.name, u.name) as name, COALESCE(d.phone, u.phone) as phone
        FROM drivers d
        LEFT JOIN users u ON d.user_id = u.id
        WHERE d.driver_id_code = ? OR d.driver_id_code = ? OR d.driver_id_code = ? OR d.id = ?
    ''', (norm_code, raw_code, no_hyphen, driver_id_code))
    row = cursor.fetchone()
    conn.close()
    return row




def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    # ──────────────────────────────────────────────────────────────────
    # Users Table (shared login)
    # ──────────────────────────────────────────────────────────────────
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL,   -- 'driver', 'doctor', 'admin', 'ambulance', 'family'
            name TEXT NOT NULL,
            phone TEXT,
            preferred_language TEXT DEFAULT 'en',
            driver_id_code TEXT,
            sub_role TEXT,
            hospital_id INTEGER,
            approval_status TEXT DEFAULT 'approved'
        )
    ''')
    # Migrate: add new columns to users if missing
    for col, defn in [
        ('phone', 'TEXT'),
        ('preferred_language', "TEXT DEFAULT 'en'"),
        ('driver_id_code', 'TEXT'),
        ('sub_role', 'TEXT'),
        ('hospital_id', 'INTEGER'),
        ('approval_status', "TEXT DEFAULT 'approved'"),
        ('failed_attempts', "INTEGER DEFAULT 0"),
        ('locked_until', "TEXT"),
        ('token_version', "INTEGER DEFAULT 0"),
        ('staff_id_code', 'TEXT'),
        ('created_at', "TEXT DEFAULT ''"),
        ('email', 'TEXT'),
        ('verified', "INTEGER DEFAULT 1"),
        ('is_active', "INTEGER DEFAULT 1"),
    ]:
        try:
            cursor.execute(f"ALTER TABLE users ADD COLUMN {col} {defn}")
        except Exception:
            pass

    try:
        cursor.execute("UPDATE users SET created_at = CURRENT_TIMESTAMP WHERE created_at IS NULL")
    except Exception:
        pass


    # ──────────────────────────────────────────────────────────────────
    # Drivers Table (linked to users)
    # ──────────────────────────────────────────────────────────────────
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS drivers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER UNIQUE NOT NULL,
            driver_id_code TEXT UNIQUE,
            age INTEGER,
            gender TEXT,
            blood_group TEXT,
            height REAL,
            weight REAL,
            medical_history TEXT,
            emergency_contacts TEXT,
            insurance TEXT,
            vehicle_number TEXT,
            driving_license TEXT,
            family_details TEXT,
            address TEXT,
            preferred_language TEXT DEFAULT 'en',
            phone TEXT,
            city TEXT,
            gps_home_lat REAL,
            gps_home_lng REAL,
            doctor_name TEXT,
            hospital_preference TEXT,
            ambulance_number TEXT,
            family_member1_name TEXT,
            family_member1_phone TEXT,
            family_member1_lang TEXT DEFAULT 'en',
            family_member1_relation TEXT,
            family_member2_name TEXT,
            family_member2_phone TEXT,
            family_member2_lang TEXT DEFAULT 'en',
            family_member2_relation TEXT,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
        )
    ''')
    # Migrate: add new driver columns if missing
    new_driver_cols = [
        ('driver_id_code',     'TEXT'),
        ('preferred_language', "TEXT DEFAULT 'en'"),
        ('phone',              'TEXT'),
        ('city',               'TEXT'),
        ('gps_home_lat',       'REAL'),
        ('gps_home_lng',       'REAL'),
        ('doctor_name',        'TEXT'),
        ('hospital_preference','TEXT'),
        ('ambulance_number',   'TEXT'),
        ('family_member1_name',  'TEXT'),
        ('family_member1_phone', 'TEXT'),
        ('family_member1_lang',  "TEXT DEFAULT 'en'"),
        ('family_member1_relation', 'TEXT'),
        ('family_member2_name',  'TEXT'),
        ('family_member2_phone', 'TEXT'),
        ('family_member2_lang',  "TEXT DEFAULT 'en'"),
        ('family_member2_relation', 'TEXT'),
        ('dob',                  'TEXT'),
        ('district',             'TEXT'),
        ('state',                'TEXT'),
        ('pincode',              'TEXT'),
        ('licence_number',       'TEXT'),
        ('licence_expiry',       'TEXT'),
        ('vehicle_type',         'TEXT'),
        ('experience',           'INTEGER DEFAULT 0'),
        ('organization',         'TEXT'),
        ('emergency_contact',    'TEXT'),
        ('medical_conditions',   'TEXT'),
        ('medications',          'TEXT'),
        ('allergies',            'TEXT'),
        ('cardiac_history',      'TEXT'),
        ('emergency_notes',      'TEXT'),
        ('status',               "TEXT DEFAULT 'ACTIVE'"),
        ('created_at',           'DATETIME'),
        ('updated_at',           'DATETIME'),
    ]
    for col, defn in new_driver_cols:
        try:
            cursor.execute(f"ALTER TABLE drivers ADD COLUMN {col} {defn}")
        except Exception:
            pass

    # Ensure family_members extended columns exist
    family_cols = [
        ('dob', 'TEXT'),
        ('gender', 'TEXT'),
        ('address', 'TEXT'),
        ('city', 'TEXT'),
        ('district', 'TEXT'),
        ('state', 'TEXT'),
        ('pincode', 'TEXT'),
        ('primary_emergency_contact', 'TEXT'),
        ('secondary_emergency_contact', 'TEXT'),
        ('notification_preferences', 'TEXT'),
        ('status', "TEXT DEFAULT 'ACTIVE'"),
        ('created_at', 'DATETIME'),
        ('updated_at', 'DATETIME'),
    ]
    for col, defn in family_cols:
        try:
            cursor.execute(f"ALTER TABLE family_members ADD COLUMN {col} {defn}")
        except Exception:
            pass

    # Ensure ambulances extended columns exist
    ambulance_cols = [
        ('ambulance_driver_id_code', 'TEXT'),
        ('ambulance_type', 'TEXT'),
        ('dob', 'TEXT'),
        ('gender', 'TEXT'),
        ('address', 'TEXT'),
        ('city', 'TEXT'),
        ('district', 'TEXT'),
        ('state', 'TEXT'),
        ('pincode', 'TEXT'),
        ('licence_number', 'TEXT'),
        ('licence_expiry', 'TEXT'),
        ('experience', 'INTEGER DEFAULT 0'),
        ('ambulance_registration_number', 'TEXT'),
        ('service_provider', 'TEXT'),
        ('organization', 'TEXT'),
        ('organization_address', 'TEXT'),
        ('emergency_contact', 'TEXT'),
        ('capabilities', 'TEXT'),
        ('last_location_update', 'DATETIME'),
        ('current_location', 'TEXT'),
        ('driver_name', 'TEXT'),
        ('driver_phone', 'TEXT'),
        ('status', "TEXT DEFAULT 'AVAILABLE'"),
        ('emergency_call_consent', 'INTEGER DEFAULT 1'),
        ('emergency_call_enabled', 'INTEGER DEFAULT 1'),
        ('phone_verified', 'INTEGER DEFAULT 1'),
        ('preferred_language', "TEXT DEFAULT 'en'"),
        ('consent_timestamp', 'DATETIME'),
        ('created_at', 'DATETIME'),
        ('driver_user_id', 'INTEGER'),
        ('service_id', 'INTEGER'),
    ]
    for col, defn in ambulance_cols:
        try:
            cursor.execute(f"ALTER TABLE ambulances ADD COLUMN {col} {defn}")
        except Exception:
            pass


    # ──────────────────────────────────────────────────────────────────
    # OTP Verifications Table (NEW)
    # ──────────────────────────────────────────────────────────────────
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS otp_verifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            phone TEXT NOT NULL,
            otp_code TEXT NOT NULL,
            purpose TEXT NOT NULL,
            expires_at DATETIME NOT NULL,
            is_verified INTEGER DEFAULT 0,
            attempts INTEGER DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Ensure columns exist on drivers table
    try:
        cursor.execute("ALTER TABLE drivers ADD COLUMN name TEXT")
    except Exception:
        pass
    try:
        cursor.execute("ALTER TABLE drivers ADD COLUMN phone TEXT")
    except Exception:
        pass
    try:
        cursor.execute("ALTER TABLE drivers ADD COLUMN email TEXT")
    except Exception:
        pass
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ambulance_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            request_id_code TEXT UNIQUE NOT NULL,
            emergency_id INTEGER NOT NULL,
            driver_id INTEGER NOT NULL,
            ambulance_id INTEGER NOT NULL,
            hospital_id INTEGER,
            latitude REAL,
            longitude REAL,
            priority TEXT DEFAULT 'CRITICAL',
            status TEXT DEFAULT 'PENDING',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            accepted_at DATETIME,
            rejected_at DATETIME,
            FOREIGN KEY (emergency_id) REFERENCES emergencies (id) ON DELETE CASCADE,
            FOREIGN KEY (driver_id) REFERENCES drivers (id) ON DELETE CASCADE,
            FOREIGN KEY (ambulance_id) REFERENCES ambulances (id) ON DELETE CASCADE,
            FOREIGN KEY (hospital_id) REFERENCES hospitals (id) ON DELETE SET NULL
        )
    ''')
    cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_amb_req_code ON ambulance_requests(request_id_code)")

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS medical_reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            report_id_code TEXT UNIQUE NOT NULL,
            driver_id INTEGER NOT NULL,
            emergency_id INTEGER NOT NULL,
            hospital_id INTEGER,
            file_path TEXT,
            pdf_bytes INTEGER,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (driver_id) REFERENCES drivers (id) ON DELETE CASCADE,
            FOREIGN KEY (emergency_id) REFERENCES emergencies (id) ON DELETE CASCADE,
            FOREIGN KEY (hospital_id) REFERENCES hospitals (id) ON DELETE SET NULL
        )
    ''')
    cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_med_rpt_code ON medical_reports(report_id_code)")

    try:
        cursor.execute("ALTER TABLE drivers ADD COLUMN updated_at DATETIME")
    except Exception:
        pass


    # Backfill missing/NULL or unformatted driver_id_code for drivers
    try:
        cursor.execute("SELECT id, driver_id_code FROM drivers WHERE driver_id_code IS NULL OR driver_id_code = '' OR driver_id_code NOT LIKE 'DRV-%'")
        unformatted = cursor.fetchall()
        for u_drv in unformatted:
            raw_code = u_drv['driver_id_code'] or ''
            digits = ''.join(c for c in raw_code if c.isdigit())
            if digits and len(digits) > 0:
                fmt_code = f"DRV-{int(digits):06d}"
            else:
                fmt_code = generate_unique_driver_id(conn)
            cursor.execute("UPDATE drivers SET driver_id_code = ? WHERE id = ?", (fmt_code, u_drv['id']))
        conn.commit()

        # Deduplicate any duplicate driver_id_code values
        cursor.execute("SELECT driver_id_code, COUNT(*) as cnt FROM drivers WHERE driver_id_code IS NOT NULL GROUP BY driver_id_code HAVING cnt > 1")
        dup_rows = cursor.fetchall()
        for dr in dup_rows:
            code = dr['driver_id_code']
            cursor.execute("SELECT id FROM drivers WHERE driver_id_code = ? ORDER BY id ASC", (code,))
            matches = cursor.fetchall()
            for match in matches[1:]:
                new_code = generate_unique_driver_id(conn)
                cursor.execute("UPDATE drivers SET driver_id_code = ? WHERE id = ?", (new_code, match['id']))
                cursor.execute("UPDATE family_members SET driver_id_code = ? WHERE driver_id = ?", (new_code, match['id']))

        cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_drivers_driver_id_code ON drivers(driver_id_code)")
    except Exception as e:
        print("[INIT_DB Migration Warning]", e)



    # Ensure columns exist on family_members table
    try:
        cursor.execute("ALTER TABLE family_members ADD COLUMN family_id_code TEXT")
    except Exception:
        pass
    try:
        cursor.execute("ALTER TABLE family_members ADD COLUMN name TEXT")
    except Exception:
        pass
    try:
        cursor.execute("ALTER TABLE family_members ADD COLUMN phone TEXT")
    except Exception:
        pass
    try:
        cursor.execute("ALTER TABLE family_members ADD COLUMN email TEXT")
    except Exception:
        pass
    try:
        cursor.execute("ALTER TABLE family_members ADD COLUMN status TEXT DEFAULT 'ACTIVE'")
    except Exception:
        pass
    try:
        cursor.execute("ALTER TABLE family_members ADD COLUMN emergency_sms_consent INTEGER DEFAULT 1")
    except Exception:
        pass
    try:
        cursor.execute("ALTER TABLE family_members ADD COLUMN emergency_status_consent INTEGER DEFAULT 1")
    except Exception:
        pass
    try:
        cursor.execute("ALTER TABLE family_members ADD COLUMN notification_enabled INTEGER DEFAULT 1")
    except Exception:
        pass
    try:
        cursor.execute("ALTER TABLE family_members ADD COLUMN phone_verified INTEGER DEFAULT 0")
    except Exception:
        pass
    try:
        cursor.execute("ALTER TABLE family_members ADD COLUMN consent_timestamp DATETIME")
    except Exception:
        pass


    # ──────────────────────────────────────────────────────────────────
    # Hospital Staff Table (NEW)
    # ──────────────────────────────────────────────────────────────────
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS hospital_staff (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER UNIQUE NOT NULL,
            hospital_id INTEGER NOT NULL,
            sub_role TEXT NOT NULL, -- 'reception', 'doctor', 'nurse', 'pharmacy', 'ambulance_driver'
            specialty TEXT,
            qualification TEXT,
            approval_status TEXT DEFAULT 'pending_approval',
            staff_id_code TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
            FOREIGN KEY (hospital_id) REFERENCES hospitals (id) ON DELETE CASCADE
        )
    ''')
    try:
        cursor.execute("ALTER TABLE hospital_staff ADD COLUMN staff_id_code TEXT")
    except Exception:
        pass
    try:
        cursor.execute("ALTER TABLE hospital_staff ADD COLUMN name TEXT")
    except Exception:
        pass
    try:
        cursor.execute("ALTER TABLE hospital_staff ADD COLUMN role TEXT")
    except Exception:
        pass
    try:
        cursor.execute("ALTER TABLE hospital_staff ADD COLUMN phone TEXT")
    except Exception:
        pass
    try:
        cursor.execute("ALTER TABLE hospital_staff ADD COLUMN email TEXT")
    except Exception:
        pass
    try:
        cursor.execute("ALTER TABLE hospital_staff ADD COLUMN is_active INTEGER DEFAULT 1")
    except Exception:
        pass

    # ──────────────────────────────────────────────────────────────────
    # Hospital & Ambulance Emergency Requests Tables (NEW)
    # ──────────────────────────────────────────────────────────────────
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS hospital_emergency_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            emergency_id INTEGER NOT NULL,
            hospital_id INTEGER NOT NULL,
            status TEXT DEFAULT 'notified', -- 'notified', 'accepted', 'withdrawn_other_accepted'
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (emergency_id) REFERENCES emergencies (id) ON DELETE CASCADE,
            FOREIGN KEY (hospital_id) REFERENCES hospitals (id) ON DELETE CASCADE
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ambulance_emergency_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            emergency_id INTEGER NOT NULL,
            ambulance_id INTEGER NOT NULL,
            status TEXT DEFAULT 'notified', -- 'notified', 'accepted', 'withdrawn_other_accepted'
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (emergency_id) REFERENCES emergencies (id) ON DELETE CASCADE,
            FOREIGN KEY (ambulance_id) REFERENCES ambulances (id) ON DELETE CASCADE
        )
    ''')
    for col, defn in [
        ('ambulance_driver_id', 'INTEGER'),
        ('attempt_number', 'INTEGER DEFAULT 1'),
        ('call_sid', 'TEXT'),
        ('call_started_at', 'TEXT'),
        ('call_answered_at', 'TEXT'),
        ('accepted_at', 'TEXT'),
        ('declined_at', 'TEXT'),
        ('completed_at', 'TEXT'),
        ('failure_reason', 'TEXT'),
        ('created_at', "TEXT")
    ]:
        try:
            cursor.execute(f"ALTER TABLE ambulance_emergency_requests ADD COLUMN {col} {defn}")
        except Exception:
            pass


    # ──────────────────────────────────────────────────────────────────
    # Health Logs Table
    # ──────────────────────────────────────────────────────────────────
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS health_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            driver_id INTEGER NOT NULL,
            heart_rate REAL,
            spo2 REAL,
            temperature REAL,
            systolic_bp REAL,
            diastolic_bp REAL,
            respiration_rate REAL,
            sleep_hours REAL,
            stress_level REAL,
            fatigue_score REAL,
            symptoms TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (driver_id) REFERENCES drivers (id) ON DELETE CASCADE
        )
    ''')

    # ──────────────────────────────────────────────────────────────────
    # Emergencies Table
    # ──────────────────────────────────────────────────────────────────
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS emergencies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            driver_id INTEGER NOT NULL,
            prediction TEXT,
            confidence REAL,
            risk_percentage REAL,
            severity TEXT,
            explanation TEXT,
            suggested_action TEXT,
            hospital_id INTEGER,
            ambulance_id INTEGER,
            status TEXT DEFAULT 'Active',
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            driver_lat REAL,
            driver_lng REAL,
            emergency_code TEXT,
            ai_reasoning TEXT,
            voice_log TEXT,
            notification_log TEXT,
            escalation_level INTEGER DEFAULT 1,
            consciousness_response TEXT DEFAULT 'pending',
            accepted_hospital_id INTEGER,
            accepted_ambulance_id INTEGER,
            assigned_doctor_id INTEGER,
            reception_status TEXT DEFAULT 'Pending',
            doctor_diagnosis TEXT,
            doctor_treatment TEXT,
            nursing_observations TEXT,
            patient_care_status TEXT DEFAULT 'Pending',
            prescription_text TEXT,
            hospital_notified_ids TEXT,
            hospital_status TEXT DEFAULT 'WAITING_FOR_HOSPITAL',
            ambulance_status TEXT DEFAULT 'SEARCHING',
            emergency_status TEXT DEFAULT 'CREATED',
            hospital_accepted_at DATETIME,
            ambulance_accepted_at DATETIME,
            FOREIGN KEY (driver_id) REFERENCES drivers (id) ON DELETE CASCADE,
            FOREIGN KEY (hospital_id) REFERENCES hospitals (id),
            FOREIGN KEY (ambulance_id) REFERENCES ambulances (id)
        )
    ''')
    # Migrate existing emergencies table
    new_emerg_cols = [
        ('driver_lat',            'REAL'),
        ('driver_lng',            'REAL'),
        ('emergency_code',        'TEXT'),
        ('ai_reasoning',          'TEXT'),
        ('voice_log',             'TEXT'),
        ('notification_log',      'TEXT'),
        ('escalation_level',      'INTEGER DEFAULT 1'),
        ('consciousness_response',"TEXT DEFAULT 'pending'"),
        ('hospital_notified_ids', 'TEXT'),
        ('accepted_hospital_id',  'INTEGER'),
        ('accepted_ambulance_id', 'INTEGER'),
        ('assigned_doctor_id',    'INTEGER'),
        ('reception_status',      "TEXT DEFAULT 'Pending'"),
        ('doctor_diagnosis',      'TEXT'),
        ('doctor_treatment',      'TEXT'),
        ('nursing_observations',  'TEXT'),
        ('patient_care_status',   "TEXT DEFAULT 'Pending'"),
        ('prescription_text',     'TEXT'),
        ('pharmacy_status',       "TEXT DEFAULT 'Pending'"),
        ('heart_rate',            'REAL'),
        ('spo2',                  'REAL'),
        ('temperature',           'REAL'),
        ('blood_pressure',        'TEXT'),
        ('respiration',           'REAL'),
        ('ecg_summary',           'TEXT'),
        ('accident_detected',     'INTEGER DEFAULT 0'),
        ('ai_summary',            'TEXT'),
        ('emergency_type',        'TEXT'),
        ('risk_level',            'TEXT'),
        ('hospital_status',       "TEXT DEFAULT 'WAITING_FOR_HOSPITAL'"),
        ('ambulance_status',      "TEXT DEFAULT 'SEARCHING'"),
        ('emergency_status',      "TEXT DEFAULT 'CREATED'"),
        ('hospital_accepted_at',  'DATETIME'),
        ('ambulance_accepted_at', 'DATETIME'),
    ]

    cursor.execute("PRAGMA table_info(emergencies)")
    existing_cols = set(r[1] for r in cursor.fetchall())
    for col, defn in new_emerg_cols:
        if col not in existing_cols:
            try:
                cursor.execute(f"ALTER TABLE emergencies ADD COLUMN {col} {defn}")
            except Exception as e:
                print(f"[Migration Error adding {col}]:", e)

    new_hosp_cols = [
        ('emergency_notification_consent', 'INTEGER DEFAULT 1'),
        ('emergency_phone', 'TEXT'),
        ('emergency_email', 'TEXT'),
        ('notification_enabled', 'INTEGER DEFAULT 1'),
        ('phone_verified', 'INTEGER DEFAULT 1'),
        ('consent_timestamp', 'TEXT'),
    ]
    cursor.execute("PRAGMA table_info(hospitals)")
    existing_hosp_cols = set(r[1] for r in cursor.fetchall())
    for col, defn in new_hosp_cols:
        if col not in existing_hosp_cols:
            try:
                cursor.execute(f"ALTER TABLE hospitals ADD COLUMN {col} {defn}")
            except Exception as e:
                pass
    conn.commit()

    # ──────────────────────────────────────────────────────────────────
    # Emergency Timeline Table  (NEW)
    # ──────────────────────────────────────────────────────────────────
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS emergency_timeline (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            emergency_id INTEGER NOT NULL,
            step TEXT NOT NULL,
            detail TEXT,
            status TEXT DEFAULT 'completed',
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (emergency_id) REFERENCES emergencies (id)
        )
    ''')

    # ──────────────────────────────────────────────────────────────────
    # Notifications Table  (NEW)
    # ──────────────────────────────────────────────────────────────────
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            emergency_id INTEGER NOT NULL,
            recipient_type TEXT,   -- 'family', 'hospital', 'ambulance'
            recipient_name TEXT,
            phone TEXT,
            channel TEXT,          -- 'SMS', 'CALL', 'WHATSAPP'
            message TEXT,
            status TEXT,           -- 'simulated', 'sent:SID', 'failed:...'
            lang TEXT DEFAULT 'en',
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (emergency_id) REFERENCES emergencies (id)
        )
    ''')

    # ──────────────────────────────────────────────────────────────────
    # Voice Sessions Table  (NEW)
    # ──────────────────────────────────────────────────────────────────
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS voice_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            emergency_id INTEGER NOT NULL,
            session_id TEXT,
            question TEXT,
            response TEXT,
            response_time_sec INTEGER,
            escalated INTEGER DEFAULT 0,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (emergency_id) REFERENCES emergencies (id)
        )
    ''')

    # ──────────────────────────────────────────────────────────────────
    # Hospitals Table
    # ──────────────────────────────────────────────────────────────────
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS hospitals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            address TEXT NOT NULL,
            latitude REAL NOT NULL,
            longitude REAL NOT NULL,
            emergency_types TEXT,
            emergency_number TEXT,
            availability INTEGER DEFAULT 1,
            preferred_language TEXT DEFAULT 'en',
            hospital_id_code TEXT UNIQUE,
            hospital_type TEXT,
            email TEXT,
            city TEXT,
            district TEXT DEFAULT 'Erode',
            state TEXT DEFAULT 'Tamil Nadu',
            pincode TEXT,
            icu_availability INTEGER DEFAULT 1,
            cardiology_availability INTEGER DEFAULT 1,
            neurology_availability INTEGER DEFAULT 1,
            available_beds INTEGER DEFAULT 10,
            icu_beds INTEGER DEFAULT 5,
            ambulance_availability INTEGER DEFAULT 1,
            username TEXT,
            password TEXT,
            google_place_id TEXT,
            place_id TEXT,
            rating REAL DEFAULT 4.5,
            review_count INTEGER DEFAULT 100,
            website TEXT,
            maps_url TEXT,
            emergency_available INTEGER DEFAULT 1,
            verified INTEGER DEFAULT 1,
            source TEXT DEFAULT 'Admin Verified',
            opening_hours_json TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    for col, defn in [
        ('preferred_language', "TEXT DEFAULT 'en'"),
        ('hospital_id_code', 'TEXT'),
        ('hospital_type', "TEXT DEFAULT 'Multi-Speciality'"),
        ('email', 'TEXT'),
        ('city', "TEXT DEFAULT 'Erode'"),
        ('district', "TEXT DEFAULT 'Erode'"),
        ('state', "TEXT DEFAULT 'Tamil Nadu'"),
        ('pincode', 'TEXT'),
        ('icu_availability', 'INTEGER DEFAULT 1'),
        ('cardiology_availability', 'INTEGER DEFAULT 1'),
        ('neurology_availability', 'INTEGER DEFAULT 1'),
        ('available_beds', 'INTEGER DEFAULT 10'),
        ('icu_beds', 'INTEGER DEFAULT 5'),
        ('ambulance_availability', 'INTEGER DEFAULT 1'),
        ('username', 'TEXT'),
        ('password', 'TEXT'),
        ('google_place_id', 'TEXT'),
        ('place_id', 'TEXT'),
        ('rating', 'REAL DEFAULT 4.5'),
        ('review_count', 'INTEGER DEFAULT 100'),
        ('website', 'TEXT'),
        ('maps_url', 'TEXT'),
        ('emergency_available', 'INTEGER DEFAULT 1'),
        ('verified', 'INTEGER DEFAULT 1'),
        ('source', "TEXT DEFAULT 'Admin Verified'"),
        ('opening_hours_json', 'TEXT'),
        ('status', "TEXT DEFAULT 'ACTIVE'"),
        ('has_er', "INTEGER DEFAULT 1"),
        ('has_icu', "INTEGER DEFAULT 1"),
        ('has_cardiology', "INTEGER DEFAULT 0"),
        ('has_neurology', "INTEGER DEFAULT 0"),
        ('has_nephrology', "INTEGER DEFAULT 0"),
        ('has_general', "INTEGER DEFAULT 1"),
        ('emergency_notification_consent', "INTEGER DEFAULT 1"),
        ('emergency_phone', 'TEXT'),
        ('emergency_email', 'TEXT'),
        ('notification_enabled', "INTEGER DEFAULT 1"),
        ('phone_verified', "INTEGER DEFAULT 0"),
        ('consent_timestamp', 'DATETIME'),
        ('created_at', 'DATETIME'),
        ('updated_at', 'DATETIME'),
        ('admin_user_id', 'INTEGER')
    ]:

        try:
            cursor.execute(f"ALTER TABLE hospitals ADD COLUMN {col} {defn}")
        except Exception:
            pass

    for col, defn in [
        ('phone', 'TEXT'),
        ('email', 'TEXT'),
        ('hospital_id', 'INTEGER'),
        ('verified', 'INTEGER DEFAULT 0'),
        ('status', "TEXT DEFAULT 'ACTIVE'"),
        ('is_active', 'INTEGER DEFAULT 1')
    ]:
        try:
            cursor.execute(f"ALTER TABLE users ADD COLUMN {col} {defn}")
        except Exception:
            pass

    for col, defn in [
        ('hospital_id', 'INTEGER'),
        ('driver_user_id', 'INTEGER'),
        ('status', "TEXT DEFAULT 'AVAILABLE'")
    ]:
        try:
            cursor.execute(f"ALTER TABLE ambulances ADD COLUMN {col} {defn}")
        except Exception:
            pass

    for col, defn in [
        ('user_id', 'INTEGER'),
        ('doctor_id_code', 'TEXT'),
        ('phone', 'TEXT'),
        ('email', 'TEXT'),
        ('gender', 'TEXT'),
        ('dob', 'TEXT'),
        ('reg_number', 'TEXT'),
        ('emergency_dept', 'TEXT'),
        ('is_active', 'INTEGER DEFAULT 1'),
        ('status', "TEXT DEFAULT 'ACTIVE'")
    ]:
        try:
            cursor.execute(f"ALTER TABLE doctors ADD COLUMN {col} {defn}")
        except Exception:
            pass

    for col, defn in [
        ('status', "TEXT DEFAULT 'ACTIVE'"),
        ('is_active', 'INTEGER DEFAULT 1')
    ]:
        try:
            cursor.execute(f"ALTER TABLE hospital_staff ADD COLUMN {col} {defn}")
        except Exception:
            pass


    # Hospital Specialties Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS hospital_specialties (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            hospital_id INTEGER NOT NULL,
            specialty TEXT NOT NULL,
            verified INTEGER DEFAULT 1,
            source TEXT DEFAULT 'Admin Verified',
            FOREIGN KEY (hospital_id) REFERENCES hospitals (id) ON DELETE CASCADE
        )
    ''')

    # Hospital Services Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS hospital_services (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            hospital_id INTEGER NOT NULL,
            service_name TEXT NOT NULL,
            verified INTEGER DEFAULT 1,
            source TEXT DEFAULT 'Admin Verified',
            FOREIGN KEY (hospital_id) REFERENCES hospitals (id) ON DELETE CASCADE
        )
    ''')

    # Hospital Working Hours Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS hospital_working_hours (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            hospital_id INTEGER NOT NULL,
            day TEXT NOT NULL, -- Monday, Tuesday, ... Sunday
            opening_time TEXT DEFAULT '08:00 AM',
            closing_time TEXT DEFAULT '10:00 PM',
            is_open_24h INTEGER DEFAULT 0,
            source TEXT DEFAULT 'Admin Verified',
            FOREIGN KEY (hospital_id) REFERENCES hospitals (id) ON DELETE CASCADE
        )
    ''')

    # Doctors Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS doctors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER UNIQUE,
            hospital_id INTEGER NOT NULL,
            doctor_id_code TEXT UNIQUE,
            name TEXT NOT NULL,
            phone TEXT,
            email TEXT,
            gender TEXT,
            dob TEXT,
            reg_number TEXT,
            specialty TEXT NOT NULL,
            qualification TEXT,
            experience TEXT,
            emergency_dept TEXT,
            availability TEXT DEFAULT 'Monday - Saturday',
            working_days TEXT DEFAULT 'Mon - Sat',
            working_hours TEXT DEFAULT '10:00 AM - 04:00 PM',
            contact_info TEXT,
            verified INTEGER DEFAULT 1,
            source TEXT DEFAULT 'Admin Verified',
            is_active INTEGER DEFAULT 1,
            FOREIGN KEY (hospital_id) REFERENCES hospitals (id) ON DELETE CASCADE,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
        )
    ''')

    # Nurses Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS nurses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER UNIQUE,
            hospital_id INTEGER NOT NULL,
            nurse_id_code TEXT UNIQUE,
            name TEXT NOT NULL,
            phone TEXT,
            email TEXT,
            gender TEXT,
            qualification TEXT,
            nursing_reg_number TEXT,
            department TEXT,
            shift TEXT DEFAULT 'Day',
            is_active INTEGER DEFAULT 1,
            FOREIGN KEY (hospital_id) REFERENCES hospitals (id) ON DELETE CASCADE,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
        )
    ''')

    # Receptionists Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS receptionists (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER UNIQUE,
            hospital_id INTEGER NOT NULL,
            receptionist_id_code TEXT UNIQUE,
            name TEXT NOT NULL,
            phone TEXT,
            email TEXT,
            shift TEXT DEFAULT 'Day',
            is_active INTEGER DEFAULT 1,
            FOREIGN KEY (hospital_id) REFERENCES hospitals (id) ON DELETE CASCADE,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
        )
    ''')

    # Pharmacists Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS pharmacists (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER UNIQUE,
            hospital_id INTEGER NOT NULL,
            pharmacist_id_code TEXT UNIQUE,
            name TEXT NOT NULL,
            phone TEXT,
            email TEXT,
            pharmacy_reg_number TEXT,
            qualification TEXT,
            department TEXT DEFAULT 'Pharmacy',
            is_active INTEGER DEFAULT 1,
            FOREIGN KEY (hospital_id) REFERENCES hospitals (id) ON DELETE CASCADE,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
        )
    ''')

    # Ambulance Drivers Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ambulance_drivers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER UNIQUE,
            hospital_id INTEGER NOT NULL,
            driver_id_code TEXT UNIQUE,
            name TEXT NOT NULL,
            phone TEXT,
            email TEXT,
            license_number TEXT,
            license_expiry TEXT,
            ambulance_number TEXT,
            ambulance_type TEXT DEFAULT 'Basic Life Support (BLS)',
            emergency_contact TEXT,
            availability_status TEXT DEFAULT 'Available',
            current_gps_lat REAL DEFAULT 11.3410,
            current_gps_lng REAL DEFAULT 77.7170,
            is_active INTEGER DEFAULT 1,
            FOREIGN KEY (hospital_id) REFERENCES hospitals (id) ON DELETE CASCADE,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
        )
    ''')

    # ECG Readings Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ecg_readings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            driver_id INTEGER NOT NULL,
            heart_rate_ecg REAL,
            sdnn_ms REAL,
            rmssd_ms REAL,
            arrhythmia_detected INTEGER DEFAULT 0,
            signal_quality_sqi REAL DEFAULT 0.95,
            ecg_notes TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (driver_id) REFERENCES drivers (id) ON DELETE CASCADE
        )
    ''')

    # GPS Locations History Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS gps_locations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            driver_id INTEGER NOT NULL,
            latitude REAL NOT NULL,
            longitude REAL NOT NULL,
            speed_kmh REAL DEFAULT 0.0,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (driver_id) REFERENCES drivers (id) ON DELETE CASCADE
        )
    ''')

    # Emergency Reports Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS emergency_reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            emergency_id INTEGER UNIQUE NOT NULL,
            report_json TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (emergency_id) REFERENCES emergencies (id) ON DELETE CASCADE
        )
    ''')

    # Notification Logs Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS notification_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            emergency_id INTEGER,
            recipient_type TEXT,
            recipient_id INTEGER,
            phone TEXT,
            message TEXT,
            provider TEXT,
            status TEXT,
            provider_message_id TEXT,
            error_message TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Call Logs Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS call_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            emergency_id INTEGER,
            recipient_role TEXT,
            phone TEXT,
            status TEXT,
            provider_call_id TEXT,
            failure_reason TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    cursor.execute("SELECT id FROM hospitals WHERE hospital_id_code IS NULL OR hospital_id_code = ''")
    for r in cursor.fetchall():
        cursor.execute("UPDATE hospitals SET hospital_id_code = ? WHERE id = ?", (f"HOS-{r['id']:06d}", r['id']))
    
    # Ensure doctor1 demo user has proper hospital_id and sub_role
    cursor.execute("""
        UPDATE users
        SET role = 'hospital_staff', sub_role = 'doctor', hospital_id = 2, approval_status = 'approved'
        WHERE username = 'doctor1' AND (hospital_id IS NULL OR role != 'hospital_staff')
    """)
    conn.commit()

    # ──────────────────────────────────────────────────────────────────
    # Ambulances Table
    # ──────────────────────────────────────────────────────────────────
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ambulances (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            vehicle_number TEXT UNIQUE NOT NULL,
            driver_name TEXT,
            driver_phone TEXT,
            latitude REAL NOT NULL,
            longitude REAL NOT NULL,
            status TEXT DEFAULT 'Available',
            eta_minutes INTEGER DEFAULT NULL,
            user_id INTEGER,
            preferred_language TEXT DEFAULT 'en',
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    for col, defn in [('user_id', 'INTEGER'), ('preferred_language', "TEXT DEFAULT 'en'")]:
        try:
            cursor.execute(f"ALTER TABLE ambulances ADD COLUMN {col} {defn}")
        except Exception:
            pass

    # ──────────────────────────────────────────────────────────────────
    # Security Logs Table (NEW)
    # ──────────────────────────────────────────────────────────────────
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS security_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ip_address TEXT,
            username TEXT,
            event_type TEXT,
            severity TEXT,
            details TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # ──────────────────────────────────────────────────────────────────
    # Audit Logs Table (NEW)
    # ──────────────────────────────────────────────────────────────────
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            username TEXT,
            action TEXT,
            ip_address TEXT,
            details TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # ──────────────────────────────────────────────────────────────────
    # Voice Conversations Table (NEW)
    # ──────────────────────────────────────────────────────────────────
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS voice_conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            session_id TEXT,
            role TEXT,
            text TEXT,
            language TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
        )
    ''')

    # ──────────────────────────────────────────────────────────────────
    # Hospital Departments Table (NEW)
    # ──────────────────────────────────────────────────────────────────
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS hospital_departments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            hospital_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            head_doctor_id INTEGER,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (hospital_id) REFERENCES hospitals (id) ON DELETE CASCADE
        )
    ''')

    # ──────────────────────────────────────────────────────────────────
    # Beds Table (NEW)
    # ──────────────────────────────────────────────────────────────────
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS beds (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            hospital_id INTEGER NOT NULL,
            bed_number TEXT NOT NULL,
            type TEXT NOT NULL DEFAULT 'General', -- 'General', 'ICU', 'ICU-Cardiology', 'ICU-Neurology'
            status TEXT NOT NULL DEFAULT 'Available', -- 'Available', 'Occupied'
            patient_id INTEGER,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (hospital_id) REFERENCES hospitals (id) ON DELETE CASCADE
        )
    ''')

    # ──────────────────────────────────────────────────────────────────
    # Patients & Admissions Tables (NEW)
    # ──────────────────────────────────────────────────────────────────
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS patients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            hospital_id INTEGER NOT NULL,
            driver_id_code TEXT,
            name TEXT NOT NULL,
            age INTEGER,
            gender TEXT,
            blood_group TEXT,
            allergies TEXT,
            medical_history TEXT,
            current_status TEXT DEFAULT 'Admitted', -- 'Admitted', 'Discharged', 'In ER'
            bed_id INTEGER,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (hospital_id) REFERENCES hospitals (id) ON DELETE CASCADE
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS hospital_admissions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            emergency_id INTEGER,
            hospital_id INTEGER NOT NULL,
            patient_name TEXT,
            age INTEGER,
            gender TEXT,
            blood_group TEXT,
            driver_id INTEGER,
            doctor_id INTEGER,
            nurse_id INTEGER,
            ward TEXT,
            bed_number TEXT,
            status TEXT DEFAULT 'ADMITTED',
            admitted_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            discharged_at DATETIME,
            FOREIGN KEY (hospital_id) REFERENCES hospitals (id) ON DELETE CASCADE
        )
    ''')

    # ──────────────────────────────────────────────────────────────────
    # Prescriptions Table (NEW)
    # ──────────────────────────────────────────────────────────────────
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS prescriptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            hospital_id INTEGER NOT NULL,
            emergency_id INTEGER,
            patient_id INTEGER NOT NULL,
            doctor_id INTEGER NOT NULL,
            doctor_name TEXT NOT NULL,
            diagnosis TEXT,
            treatment TEXT,
            medicines_json TEXT, -- JSON string containing list of medicines and dosage
            status TEXT DEFAULT 'Pending', -- 'Pending', 'Dispensed'
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (hospital_id) REFERENCES hospitals (id) ON DELETE CASCADE,
            FOREIGN KEY (patient_id) REFERENCES patients (id) ON DELETE CASCADE,
            FOREIGN KEY (doctor_id) REFERENCES users (id)
        )
    ''')

    # ──────────────────────────────────────────────────────────────────
    # Medicines Table (NEW)
    # ──────────────────────────────────────────────────────────────────
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS medicines (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            hospital_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            stock_quantity INTEGER DEFAULT 0,
            unit TEXT DEFAULT 'tablets',
            low_stock_threshold INTEGER DEFAULT 10,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (hospital_id) REFERENCES hospitals (id) ON DELETE CASCADE
        )
    ''')

    # ──────────────────────────────────────────────────────────────────
    # Medical Bills Table (NEW)
    # ──────────────────────────────────────────────────────────────────
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS medical_bills (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bill_id_code TEXT UNIQUE NOT NULL,
            hospital_id INTEGER NOT NULL,
            patient_id INTEGER NOT NULL,
            emergency_id INTEGER,
            admission_id INTEGER,
            doctor_id INTEGER,
            patient_name TEXT NOT NULL,
            admission_date TEXT,
            discharge_date TEXT,
            doctor_name TEXT,
            diagnosis TEXT,
            treatment TEXT,
            consultation_fee REAL DEFAULT 500.0,
            emergency_fee REAL DEFAULT 1000.0,
            bed_charges REAL DEFAULT 1500.0,
            icu_charges REAL DEFAULT 0.0,
            lab_charges REAL DEFAULT 500.0,
            ecg_charges REAL DEFAULT 500.0,
            medicine_subtotal REAL DEFAULT 0.0,
            other_charges REAL DEFAULT 0.0,
            discount REAL DEFAULT 0.0,
            tax_amount REAL DEFAULT 0.0,
            grand_total REAL NOT NULL,
            payment_status TEXT DEFAULT 'Pending',
            payment_method TEXT DEFAULT 'Cash',
            authorized_staff TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (hospital_id) REFERENCES hospitals (id) ON DELETE CASCADE,
            FOREIGN KEY (patient_id) REFERENCES patients (id) ON DELETE CASCADE
        )
    ''')

    # ──────────────────────────────────────────────────────────────────
    # Bill Items Table (NEW)
    # ──────────────────────────────────────────────────────────────────
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS bill_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bill_id INTEGER NOT NULL,
            item_name TEXT NOT NULL,
            category TEXT DEFAULT 'Medicine',
            quantity INTEGER DEFAULT 1,
            unit_price REAL NOT NULL,
            total_price REAL NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (bill_id) REFERENCES medical_bills (id) ON DELETE CASCADE
        )
    ''')

    # ──────────────────────────────────────────────────────────────────
    # Patient Medical History Table (NEW)
    # ──────────────────────────────────────────────────────────────────
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS patient_medical_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id INTEGER NOT NULL,
            driver_id INTEGER,
            emergency_id INTEGER,
            visit_date DATETIME DEFAULT CURRENT_TIMESTAMP,
            hospital_name TEXT,
            doctor_name TEXT,
            diagnosis TEXT,
            treatment TEXT,
            prescriptions_summary TEXT,
            report_id_code TEXT,
            bill_id_code TEXT,
            allergies TEXT,
            vitals_summary TEXT,
            admission_status TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (patient_id) REFERENCES patients (id) ON DELETE CASCADE
        )
    ''')

    # ──────────────────────────────────────────────────────────────────
    # Patient Medical Documents Table
    # ──────────────────────────────────────────────────────────────────
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS patient_medical_documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id INTEGER NOT NULL,
            document_type TEXT,
            hospital_id INTEGER,
            uploaded_date DATETIME DEFAULT CURRENT_TIMESTAMP,
            file_path TEXT,
            description TEXT,
            FOREIGN KEY (patient_id) REFERENCES patients (id) ON DELETE CASCADE
        )
    ''')

    # Migrate columns for patients and medical_reports if missing
    for col, defn in [
        ('patient_id_code', 'TEXT'),
        ('driver_id', 'INTEGER'),
        ('phone', 'TEXT'),
        ('emergency_contact', 'TEXT'),
        ('previous_diseases', 'TEXT'),
    ]:
        try:
            cursor.execute(f"ALTER TABLE patients ADD COLUMN {col} {defn}")
        except Exception:
            pass

    for col, defn in [
        ('report_id_code', 'TEXT'),
        ('patient_id', 'INTEGER'),
        ('hospital_id', 'INTEGER'),
        ('doctor_id', 'INTEGER'),
        ('diagnosis', 'TEXT'),
        ('treatment', 'TEXT'),
        ('prescription_text', 'TEXT'),
        ('pdf_filename', 'TEXT'),
    ]:
        try:
            cursor.execute(f"ALTER TABLE medical_reports ADD COLUMN {col} {defn}")
        except Exception:
            pass

    conn.commit()
    seed_data(conn)
    conn.close()
    print("Database initialized and pre-seeded successfully.")



def seed_data(conn):
    cursor = conn.cursor()

    # Seed Users
    cursor.execute("SELECT COUNT(*) FROM users")
    if cursor.fetchone()[0] == 0:
        users = [
            ('driver1',    'password123', 'driver',    'Lithhish',                  '+91 9876543200', 'ta'),
            ('doctor1',    'password123', 'doctor',    'Dr. Clara',                 '+91 9000200010', 'en'),
            ('admin1',     'password123', 'admin',     'System Guardian Admin',     '+91 9000300010', 'en'),
            ('ambulance1', 'password123', 'ambulance', 'Rajesh Kumar',              '+91 9000100010', 'ta'),
            ('family1',    'password123', 'family',    'Ravindran (Father)',         '+91 9876543210', 'ta'),
        ]
        cursor.executemany(
            "INSERT INTO users (username, password, role, name, phone, preferred_language) VALUES (?, ?, ?, ?, ?, ?)",
            users
        )
        conn.commit()

        # Seed Driver for Lithhish
        cursor.execute("SELECT id FROM users WHERE username = 'driver1'")
        driver_user_id = cursor.fetchone()[0]
        cursor.execute("UPDATE users SET driver_id_code = 'DRV000001' WHERE id = ?", (driver_user_id,))
        cursor.execute('''
            INSERT INTO drivers (user_id, driver_id_code, age, gender, blood_group, height, weight,
                                 medical_history, emergency_contacts, insurance,
                                 vehicle_number, driving_license, family_details, address,
                                 preferred_language, phone, city,
                                 gps_home_lat, gps_home_lng,
                                 doctor_name, hospital_preference, ambulance_number,
                                 family_member1_name, family_member1_phone, family_member1_lang, family_member1_relation,
                                 family_member2_name, family_member2_phone, family_member2_lang, family_member2_relation)
            VALUES (?, 'DRV000001', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            driver_user_id, 24, 'Male', 'O+', 175.5, 72.0,
            'None',
            'Dad: 9876543210, Mom: 9876543211',
            'HDFC ERGO Health - Pol #9827412',
            'TN-33-AX-1234', 'DL-14202300089',
            'Father: Ravindran, Mother: Shanthi',
            '12, Garden Street, Perundurai, Erode - 638052',
            'ta', '+91 9876543200', 'Perundurai',
            11.2720, 77.5920,
            'Dr. Suresh Babu', 'Thangam Hospital', '108',
            'Ravindran', '+91 9876543210', 'ta', 'Father',
            'Shanthi', '+91 9876543211', 'ta', 'Mother'
        ))
        driver_db_id = cursor.lastrowid
        conn.commit()

        # Link family1 user to DRV000001
        cursor.execute("SELECT id FROM users WHERE username = 'family1'")
        fam_row = cursor.fetchone()
        if fam_row:
            fam_user_id = fam_row[0]
            cursor.execute('''
                INSERT INTO family_members (user_id, driver_id, driver_id_code, relation)
                VALUES (?, ?, 'DRV000001', 'Father')
            ''', (fam_user_id, driver_db_id))
            conn.commit()

        # Link ambulance1 user to ambulance record
        cursor.execute("SELECT id FROM users WHERE username = 'ambulance1'")
        amb_user_id = cursor.fetchone()[0]
        # Will be updated when ambulances are seeded below

    # Seed Erode District Hospitals, Specialties, Doctors, Services, and Working Hours
    seed_erode_hospitals(conn)

    # Seed Ambulances
    cursor.execute("SELECT COUNT(*) FROM ambulances")
    if cursor.fetchone()[0] == 0:
        # Fetch ambulance1 user id
        cursor.execute("SELECT id FROM users WHERE username = 'ambulance1'")
        row = cursor.fetchone()
        amb_user_id = row[0] if row else None

        ambulances = [
            ('TN-33-AA-1111', 'Rajesh Kumar',    '+91 9000100010', 11.2800, 77.5900, 'Available', None, amb_user_id, 'ta'),
            ('TN-33-BB-2222', 'Suresh Raina',    '+91 9000100020', 11.2710, 77.5820, 'Available', None, None,        'ta'),
            ('TN-33-CC-3333', 'Vignesh Shivan',  '+91 9000100030', 11.3390, 77.7120, 'Available', None, None,        'en'),
            ('TN-33-DD-4444', 'Kumar Sanu',      '+91 9000100040', 11.0400, 77.0300, 'Available', None, None,        'hi'),
            ('TN-33-EE-5555', 'Anand Kumar',     '+91 9000100050', 11.2745, 77.5875, 'Available', None, None,        'ta'),
        ]
        cursor.executemany('''
            INSERT INTO ambulances (vehicle_number, driver_name, driver_phone, latitude, longitude, status, eta_minutes, user_id, preferred_language)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', ambulances)
        conn.commit()


def seed_erode_hospitals(conn):
    cursor = conn.cursor()
    
    # List of authentic Erode District Hospitals
    erode_hospitals_data = [
        {
            "name": "Lotus Hospital & Research Centre",
            "address": "Poondurai Road, Near Railway Station, Erode, Tamil Nadu 638002",
            "lat": 11.3410,
            "lng": 77.7170,
            "emergency_types": "Cardiology, Pulmonology, Neurology, Emergency Medicine, Critical Care / ICU, Orthopaedics, Trauma Care",
            "phone": "+91 424 228 2828",
            "hospital_type": "Multi-Speciality",
            "city": "Erode",
            "district": "Erode",
            "state": "Tamil Nadu",
            "pincode": "638002",
            "rating": 4.6,
            "review_count": 1240,
            "website": "https://lotushospitalerode.org",
            "emergency_available": 1,
            "verified": 1,
            "source": "Admin Verified",
            "specialties": ["Cardiology", "Pulmonology", "Neurology", "Emergency Medicine", "Critical Care / ICU", "Orthopaedics", "General Medicine", "Gastroenterology"],
            "services": ["24/7 Emergency Care", "ICU", "Cardiac Cath Lab", "CT Scan & MRI", "Diagnostic Laboratory", "Dialysis Unit"],
            "doctors": [
                {"name": "Dr. S. K. Subramanian", "specialty": "Cardiology", "qualification": "MD, DM (Cardiology)", "experience": "18 Years", "availability": "Mon - Sat", "working_hours": "09:30 AM - 03:30 PM", "contact": "+91 424 228 2828 Ext 101"},
                {"name": "Dr. P. Ramesh", "specialty": "Pulmonology", "qualification": "MD (Resp Med), DTCD", "experience": "14 Years", "availability": "Mon - Sat", "working_hours": "10:00 AM - 04:00 PM", "contact": "+91 424 228 2828 Ext 104"}
            ]
        },
        {
            "name": "Thangam Hospital",
            "address": "54, Perundurai Road, Near Collectorate, Erode, Tamil Nadu 638011",
            "lat": 11.3450,
            "lng": 77.7250,
            "emergency_types": "Cardiology, Neurology, Orthopaedics, Emergency Medicine, Critical Care / ICU, Paediatrics",
            "phone": "+91 424 222 5555",
            "hospital_type": "Multi-Speciality",
            "city": "Erode",
            "district": "Erode",
            "state": "Tamil Nadu",
            "pincode": "638011",
            "rating": 4.5,
            "review_count": 890,
            "website": "https://thangamhospital.com",
            "emergency_available": 1,
            "verified": 1,
            "source": "Admin Verified",
            "specialties": ["Cardiology", "Neurology", "Orthopaedics", "Emergency Medicine", "Critical Care / ICU", "Paediatrics", "Obstetrics & Gynaecology"],
            "services": ["Emergency Trauma Care", "Neonatal ICU", "Surgical ICU", "24/7 Pharmacy", "Blood Bank Support"],
            "doctors": [
                {"name": "Dr. K. Thangavelu", "specialty": "Neurology", "qualification": "MD, DM (Neurology)", "experience": "22 Years", "availability": "Mon - Sat", "working_hours": "10:00 AM - 02:00 PM", "contact": "+91 424 222 5555 Ext 201"},
                {"name": "Dr. M. Priya", "specialty": "Obstetrics & Gynaecology", "qualification": "MS (OBG), DGO", "experience": "15 Years", "availability": "Mon - Sat", "working_hours": "11:00 AM - 05:00 PM", "contact": "+91 424 222 5555 Ext 205"}
            ]
        },
        {
            "name": "Government Headquarters Hospital (GH Erode)",
            "address": "EVN Road, Near Railway Station, Erode, Tamil Nadu 638009",
            "lat": 11.3385,
            "lng": 77.7202,
            "emergency_types": "Emergency Medicine, Trauma Care, Critical Care / ICU, General Medicine, General Surgery, Paediatrics, Orthopaedics, Pulmonology",
            "phone": "+91 424 225 8321",
            "hospital_type": "Government",
            "city": "Erode",
            "district": "Erode",
            "state": "Tamil Nadu",
            "pincode": "638009",
            "rating": 4.2,
            "review_count": 1560,
            "website": "https://tnhealth.tn.gov.in",
            "emergency_available": 1,
            "verified": 1,
            "source": "Admin Verified",
            "specialties": ["Emergency Medicine", "Trauma Care", "Critical Care / ICU", "General Medicine", "General Surgery", "Paediatrics", "Orthopaedics", "Pulmonology"],
            "services": ["24/7 Free Emergency", "Trauma Care Unit", "Blood Bank", "Free Ambulance Service", "Government Health Scheme (CMCHS)"],
            "doctors": [
                {"name": "Dr. V. Arumugam", "specialty": "Emergency Medicine", "qualification": "MS (Gen Surg), CMO", "experience": "25 Years", "availability": "Daily (24/7 Duty Roster)", "working_hours": "08:00 AM - 08:00 PM", "contact": "+91 424 225 8321"},
                {"name": "Dr. S. Kavitha", "specialty": "Paediatrics", "qualification": "MD (Paediatrics)", "experience": "14 Years", "availability": "Mon - Sat", "working_hours": "09:00 AM - 02:00 PM", "contact": "+91 424 225 8321"}
            ]
        },
        {
            "name": "Government Medical College Hospital, Perundurai",
            "address": "Kochi - Salem Highway, Sanatorium Post, Perundurai, Erode, Tamil Nadu 638053",
            "lat": 11.2750,
            "lng": 77.5850,
            "emergency_types": "Pulmonology / Chest Medicine, Trauma Care, Critical Care / ICU, Nephrology, General Medicine, Orthopaedics, Cardiology",
            "phone": "+91 4294 220 200",
            "hospital_type": "Government",
            "city": "Perundurai",
            "district": "Erode",
            "state": "Tamil Nadu",
            "pincode": "638053",
            "rating": 4.4,
            "review_count": 2100,
            "website": "https://irtpmc.ac.in",
            "emergency_available": 1,
            "verified": 1,
            "source": "Admin Verified",
            "specialties": ["Pulmonology", "Trauma Care", "Critical Care / ICU", "Nephrology", "General Medicine", "Orthopaedics", "Cardiology"],
            "services": ["Respiratory & Chest Disease Specialty", "Highway Emergency Trauma Center", "Dialysis Center", "24/7 ICU & Ventilator Support"],
            "doctors": [
                {"name": "Dr. R. Manoharan", "specialty": "Pulmonology", "qualification": "MD (Pulmonology)", "experience": "20 Years", "availability": "Mon - Sat", "working_hours": "09:00 AM - 03:00 PM", "contact": "+91 4294 220 200 Ext 12"},
                {"name": "Dr. C. Vijay", "specialty": "Orthopaedics", "qualification": "MS (Orthopaedics)", "experience": "16 Years", "availability": "Mon - Sat", "working_hours": "09:30 AM - 03:30 PM", "contact": "+91 4294 220 200 Ext 15"}
            ]
        },
        {
            "name": "KMCH Speciality Hospital, Erode",
            "address": "Perundurai Road, Near New Bus Stand, Erode, Tamil Nadu 638011",
            "lat": 11.3482,
            "lng": 77.7125,
            "emergency_types": "Cardiology, Neurology, Nephrology, Urology, Oncology, Gastroenterology, Critical Care / ICU, Radiology",
            "phone": "+91 424 226 2626",
            "hospital_type": "Multi-Speciality",
            "city": "Erode",
            "district": "Erode",
            "state": "Tamil Nadu",
            "pincode": "638011",
            "rating": 4.7,
            "review_count": 1750,
            "website": "https://kmchhospitals.com",
            "emergency_available": 1,
            "verified": 1,
            "source": "Admin Verified",
            "specialties": ["Cardiology", "Neurology", "Nephrology", "Urology", "Oncology", "Gastroenterology", "Critical Care / ICU", "Radiology"],
            "services": ["Comprehensive Cardiac Care", "Neurology & Stroke Center", "Advanced Cancer Care / Oncology", "24/7 Trauma Emergency", "Kidney Care & Urology"],
            "doctors": [
                {"name": "Dr. N. Nallasamy", "specialty": "Cardiology", "qualification": "MD, DM (Cardiology)", "experience": "19 Years", "availability": "Mon - Sat", "working_hours": "10:00 AM - 04:00 PM", "contact": "+91 424 226 2626 Ext 301"},
                {"name": "Dr. S. Rajendran", "specialty": "Nephrology", "qualification": "MD, DM (Nephrology)", "experience": "15 Years", "availability": "Mon - Fri", "working_hours": "10:30 AM - 03:30 PM", "contact": "+91 424 226 2626 Ext 304"}
            ]
        },
        {
            "name": "Sudha Hospitals",
            "address": "162, Perundurai Road, Erode, Tamil Nadu 638011",
            "lat": 11.3435,
            "lng": 77.7210,
            "emergency_types": "Obstetrics & Gynaecology, Paediatrics, Emergency Medicine, Critical Care / ICU, General Medicine, ENT, Dermatology",
            "phone": "+91 424 225 9333",
            "hospital_type": "Private",
            "city": "Erode",
            "district": "Erode",
            "state": "Tamil Nadu",
            "pincode": "638011",
            "rating": 4.5,
            "review_count": 1120,
            "website": "https://sudhahospitals.com",
            "emergency_available": 1,
            "verified": 1,
            "source": "Admin Verified",
            "specialties": ["Obstetrics & Gynaecology", "Paediatrics", "Emergency Medicine", "Critical Care / ICU", "General Medicine", "ENT", "Dermatology"],
            "services": ["Maternity & Fertility Care", "Pediatric ICU", "24/7 Pharmacy", "Diagnostic Lab", "Cosmetic Dermatology"],
            "doctors": [
                {"name": "Dr. S. Dhanabagyam", "specialty": "Obstetrics & Gynaecology", "qualification": "MS (OBG), DGO", "experience": "28 Years", "availability": "Mon - Sat", "working_hours": "09:00 AM - 01:00 PM", "contact": "+91 424 225 9333"},
                {"name": "Dr. A. Suresh", "specialty": "Dermatology", "qualification": "MD (Dermatology)", "experience": "11 Years", "availability": "Mon - Sat", "working_hours": "04:00 PM - 08:00 PM", "contact": "+91 424 225 9333"}
            ]
        },
        {
            "name": "Erode Trust Hospital",
            "address": "Brough Road, Near Clock Tower, Erode, Tamil Nadu 638001",
            "lat": 11.3402,
            "lng": 77.7285,
            "emergency_types": "Orthopaedics, Trauma Care, Ophthalmology, ENT, General Medicine, Emergency Medicine",
            "phone": "+91 424 226 5000",
            "hospital_type": "Private",
            "city": "Erode",
            "district": "Erode",
            "state": "Tamil Nadu",
            "pincode": "638001",
            "rating": 4.3,
            "review_count": 650,
            "website": "https://erodetrusthospital.com",
            "emergency_available": 1,
            "verified": 1,
            "source": "Admin Verified",
            "specialties": ["Orthopaedics", "Trauma Care", "Ophthalmology", "ENT", "General Medicine", "Emergency Medicine"],
            "services": ["Joint Replacement Clinic", "Cataract & Eye Surgery", "24/7 Accident & Emergency", "X-Ray & Ultrasound"],
            "doctors": [
                {"name": "Dr. P. Natarajan", "specialty": "Orthopaedics", "qualification": "MS (Ortho)", "experience": "21 Years", "availability": "Mon - Sat", "working_hours": "10:00 AM - 02:00 PM", "contact": "+91 424 226 5000"},
                {"name": "Dr. M. Deepa", "specialty": "Ophthalmology", "qualification": "MS (Ophthalmology)", "experience": "13 Years", "availability": "Mon - Sat", "working_hours": "09:30 AM - 01:30 PM", "contact": "+91 424 226 5000"}
            ]
        },
        {
            "name": "Ganga Hospital Specialty Clinic Erode",
            "address": "Sathy Road, Near Collectorate Complex, Erode, Tamil Nadu 638003",
            "lat": 11.3520,
            "lng": 77.7150,
            "emergency_types": "Orthopaedics, Trauma Care, Plastic & Reconstructive Surgery, Emergency Medicine",
            "phone": "+91 424 221 4455",
            "hospital_type": "Multi-Speciality",
            "city": "Erode",
            "district": "Erode",
            "state": "Tamil Nadu",
            "pincode": "638003",
            "rating": 4.8,
            "review_count": 820,
            "website": "https://gangahospital.com",
            "emergency_available": 1,
            "verified": 1,
            "source": "Admin Verified",
            "specialties": ["Orthopaedics", "Trauma Care", "Emergency Medicine"],
            "services": ["Spine Surgery", "Bone & Joint Trauma", "Reconstructive Surgery", "Physiotherapy & Rehab"],
            "doctors": [
                {"name": "Dr. S. Raja", "specialty": "Orthopaedics", "qualification": "DNB (Ortho), MNAMS", "experience": "17 Years", "availability": "Mon - Sat", "working_hours": "10:00 AM - 04:00 PM", "contact": "+91 424 221 4455"}
            ]
        }
    ]

    for data in erode_hospitals_data:
        cursor.execute("SELECT id FROM hospitals WHERE name = ?", (data['name'],))
        row = cursor.fetchone()
        
        if not row:
            hosp_code = generate_unique_hospital_id(data.get('city') or 'Erode', conn)
            cursor.execute('''
                INSERT INTO hospitals (
                    name, address, latitude, longitude, emergency_types, emergency_number, availability,
                    preferred_language, hospital_id_code, hospital_type, city, district, state, pincode,
                    rating, review_count, website, emergency_available, verified, source
                ) VALUES (?, ?, ?, ?, ?, ?, 1, 'en', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                data['name'], data['address'], data['lat'], data['lng'], data['emergency_types'],
                data['phone'], hosp_code, data['hospital_type'], data['city'], data['district'],
                data['state'], data['pincode'], data['rating'], data['review_count'],
                data['website'], data['emergency_available'], data['verified'], data['source']
            ))
            hosp_id = cursor.lastrowid
        else:
            hosp_id = row['id']
            # Update existing to ensure rich data
            cursor.execute('''
                UPDATE hospitals SET
                    address = ?, latitude = ?, longitude = ?, emergency_types = ?, emergency_number = ?,
                    hospital_type = ?, city = ?, district = ?, state = ?, pincode = ?,
                    rating = ?, review_count = ?, website = ?, emergency_available = 1, verified = 1
                WHERE id = ?
            ''', (
                data['address'], data['lat'], data['lng'], data['emergency_types'], data['phone'],
                data['hospital_type'], data['city'], data['district'], data['state'], data['pincode'],
                data['rating'], data['review_count'], data['website'], hosp_id
            ))

        # Seed specialties for this hospital
        for spec in data.get('specialties', []):
            cursor.execute("SELECT id FROM hospital_specialties WHERE hospital_id = ? AND specialty = ?", (hosp_id, spec))
            if not cursor.fetchone():
                cursor.execute("INSERT INTO hospital_specialties (hospital_id, specialty, verified, source) VALUES (?, ?, 1, 'Admin Verified')", (hosp_id, spec))

        # Seed services for this hospital
        for srv in data.get('services', []):
            cursor.execute("SELECT id FROM hospital_services WHERE hospital_id = ? AND service_name = ?", (hosp_id, srv))
            if not cursor.fetchone():
                cursor.execute("INSERT INTO hospital_services (hospital_id, service_name, verified, source) VALUES (?, ?, 1, 'Admin Verified')", (hosp_id, srv))

        # Seed working hours for this hospital (Mon-Sun)
        days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        for day in days:
            cursor.execute("SELECT id FROM hospital_working_hours WHERE hospital_id = ? AND day = ?", (hosp_id, day))
            if not cursor.fetchone():
                cursor.execute('''
                    INSERT INTO hospital_working_hours (hospital_id, day, opening_time, closing_time, is_open_24h, source)
                    VALUES (?, ?, '08:00 AM', '10:00 PM', 1, 'Admin Verified')
                ''', (hosp_id, day))

        # Seed doctors for this hospital
        for doc in data.get('doctors', []):
            cursor.execute("SELECT id FROM doctors WHERE hospital_id = ? AND name = ?", (hosp_id, doc['name']))
            if not cursor.fetchone():
                cursor.execute('''
                    INSERT INTO doctors (hospital_id, name, specialty, qualification, experience, availability, working_days, working_hours, contact_info, verified, source)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1, 'Admin Verified')
                ''', (
                    hosp_id, doc['name'], doc['specialty'], doc['qualification'], doc['experience'],
                    doc['availability'], doc['availability'], doc['working_hours'], doc['contact'],
                ))

    # --- MIGRATE & STANDARDIZE ALL HOSPITALS & ADMIN USERS ---
    from werkzeug.security import generate_password_hash
    cursor.execute("SELECT id, name, city, hospital_id_code, admin_user_id, emergency_number, email FROM hospitals")
    hospitals = cursor.fetchall()
    
    for idx, h in enumerate(hospitals, start=1):
        h_id = h['id']
        curr_code = h['hospital_id_code']
        city = h['city'] or 'Erode'
        place_code = _get_place_code(city)
        expected_code = f"HOS-{place_code}-{idx:06d}"

        # Standardize hospital_id_code if not formatted
        if not curr_code or not curr_code.startswith("HOS-"):
            cursor.execute("UPDATE hospitals SET hospital_id_code = ? WHERE id = ?", (expected_code, h_id))
            curr_code = expected_code
        
        # Check if user account exists in users table for this hospital
        cursor.execute("SELECT id FROM users WHERE hospital_id = ? AND role IN ('hospital', 'hospital_admin', 'admin')", (h_id,))
        u_row = cursor.fetchone()
        
        if not u_row:
            # Create hospital admin user account
            pw_hash = generate_password_hash("hospital123", method="pbkdf2:sha256")
            uname = curr_code.lower()
            cursor.execute("SELECT id FROM users WHERE username = ?", (uname,))
            if cursor.fetchone():
                uname = f"{curr_code.lower()}_{h_id}"
            
            try:
                cursor.execute('''
                    INSERT INTO users (username, password, role, name, phone, email, hospital_id, verified)
                    VALUES (?, ?, 'hospital', ?, ?, ?, ?, 1)
                ''', (uname, pw_hash, f"{h['name']} Admin", h['emergency_number'] or f"99999000{h_id:02d}", h['email'], h_id))
                user_id = cursor.lastrowid
                cursor.execute("UPDATE hospitals SET admin_user_id = ? WHERE id = ?", (user_id, h_id))
            except Exception:
                pass


    conn.commit()



if __name__ == '__main__':
    init_db()

