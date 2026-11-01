from extensions import db
from datetime import datetime

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(50), nullable=False) # admin, driver, family, hospital, hospital_staff, ambulance_service
    name = db.Column(db.String(150), nullable=False)
    phone = db.Column(db.String(50))
    email = db.Column(db.String(150))
    verified = db.Column(db.Boolean, default=False)
    hospital_id = db.Column(db.Integer, db.ForeignKey('hospitals.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class OTPVerification(db.Model):
    __tablename__ = 'otp_verifications'
    id = db.Column(db.Integer, primary_key=True)
    phone = db.Column(db.String(50), nullable=False)
    otp = db.Column(db.String(10), nullable=False)
    purpose = db.Column(db.String(50))
    expires_at = db.Column(db.DateTime, nullable=False)
    verified = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Driver(db.Model):
    __tablename__ = 'drivers'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, unique=True)
    driver_id_code = db.Column(db.String(50), unique=True)
    age = db.Column(db.Integer)
    gender = db.Column(db.String(20))
    blood_group = db.Column(db.String(10))
    medical_history = db.Column(db.Text)
    emergency_contacts = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Family(db.Model):
    __tablename__ = 'family_members'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, unique=True)
    driver_id = db.Column(db.Integer, db.ForeignKey('drivers.id'), nullable=False)
    relation = db.Column(db.String(50))
    emergency_sms_consent = db.Column(db.Boolean, default=False)
    emergency_status_consent = db.Column(db.Boolean, default=False)
    phone_verified = db.Column(db.Boolean, default=False)
    notification_enabled = db.Column(db.Boolean, default=False)
    consent_timestamp = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Hospital(db.Model):
    __tablename__ = 'hospitals'
    id = db.Column(db.Integer, primary_key=True)
    hospital_id_code = db.Column(db.String(50), unique=True, nullable=False)
    name = db.Column(db.String(200), nullable=False)
    email = db.Column(db.String(150))
    phone = db.Column(db.String(50))
    address = db.Column(db.Text)
    city = db.Column(db.String(100), default='Erode')
    district = db.Column(db.String(100), default='Erode')
    state = db.Column(db.String(100), default='Tamil Nadu')
    pincode = db.Column(db.String(20))
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)
    emergency_types = db.Column(db.Text)
    emergency_number = db.Column(db.String(50))
    availability = db.Column(db.Integer, default=1)
    hospital_type = db.Column(db.String(100), default='Multi-Speciality')
    google_place_id = db.Column(db.String(150))
    place_id = db.Column(db.String(150))
    rating = db.Column(db.Float, default=4.5)
    review_count = db.Column(db.Integer, default=100)
    website = db.Column(db.String(255))
    maps_url = db.Column(db.String(255))
    emergency_available = db.Column(db.Boolean, default=True)
    verified = db.Column(db.Boolean, default=True)
    source = db.Column(db.String(100), default='Admin Verified')
    opening_hours_json = db.Column(db.Text)
    has_er = db.Column(db.Boolean, default=True)
    has_icu = db.Column(db.Boolean, default=True)
    has_cardiology = db.Column(db.Boolean, default=False)
    has_neurology = db.Column(db.Boolean, default=False)
    has_nephrology = db.Column(db.Boolean, default=False)
    has_general = db.Column(db.Boolean, default=True)
    admin_user_id = db.Column(db.Integer, db.ForeignKey('users.id')) # The user account that manages this hospital
    emergency_notification_consent = db.Column(db.Boolean, default=False)
    emergency_phone = db.Column(db.String(50))
    emergency_email = db.Column(db.String(150))
    notification_enabled = db.Column(db.Boolean, default=False)
    phone_verified = db.Column(db.Boolean, default=False)
    consent_timestamp = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class HospitalSpecialty(db.Model):
    __tablename__ = 'hospital_specialties'
    id = db.Column(db.Integer, primary_key=True)
    hospital_id = db.Column(db.Integer, db.ForeignKey('hospitals.id'), nullable=False)
    specialty = db.Column(db.String(150), nullable=False)
    verified = db.Column(db.Boolean, default=True)
    source = db.Column(db.String(100), default='Admin Verified')

class HospitalService(db.Model):
    __tablename__ = 'hospital_services'
    id = db.Column(db.Integer, primary_key=True)
    hospital_id = db.Column(db.Integer, db.ForeignKey('hospitals.id'), nullable=False)
    service_name = db.Column(db.String(150), nullable=False)
    verified = db.Column(db.Boolean, default=True)
    source = db.Column(db.String(100), default='Admin Verified')

class HospitalWorkingHours(db.Model):
    __tablename__ = 'hospital_working_hours'
    id = db.Column(db.Integer, primary_key=True)
    hospital_id = db.Column(db.Integer, db.ForeignKey('hospitals.id'), nullable=False)
    day = db.Column(db.String(20), nullable=False)
    opening_time = db.Column(db.String(20), default='08:00 AM')
    closing_time = db.Column(db.String(20), default='10:00 PM')
    is_open_24h = db.Column(db.Boolean, default=False)
    source = db.Column(db.String(100), default='Admin Verified')

class Doctor(db.Model):
    __tablename__ = 'doctors'
    id = db.Column(db.Integer, primary_key=True)
    hospital_id = db.Column(db.Integer, db.ForeignKey('hospitals.id'), nullable=False)
    name = db.Column(db.String(150), nullable=False)
    specialty = db.Column(db.String(150), nullable=False)
    qualification = db.Column(db.String(150))
    experience = db.Column(db.String(50))
    availability = db.Column(db.String(100), default='Monday - Saturday')
    working_days = db.Column(db.String(100), default='Mon - Sat')
    working_hours = db.Column(db.String(100), default='10:00 AM - 04:00 PM')
    contact_info = db.Column(db.String(100))
    verified = db.Column(db.Boolean, default=True)
    source = db.Column(db.String(100), default='Admin Verified')

class HospitalCache(db.Model):
    __tablename__ = 'hospital_cache'
    id = db.Column(db.Integer, primary_key=True)
    place_id = db.Column(db.String(150), unique=True)
    query_key = db.Column(db.String(255))
    response_json = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class ECGReading(db.Model):
    __tablename__ = 'ecg_readings'
    id = db.Column(db.Integer, primary_key=True)
    driver_id = db.Column(db.Integer, db.ForeignKey('drivers.id'), nullable=False)
    heart_rate_ecg = db.Column(db.Float)
    sdnn_ms = db.Column(db.Float)
    rmssd_ms = db.Column(db.Float)
    arrhythmia_detected = db.Column(db.Boolean, default=False)
    signal_quality_sqi = db.Column(db.Float, default=0.95)
    ecg_notes = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

class GPSLocation(db.Model):
    __tablename__ = 'gps_locations'
    id = db.Column(db.Integer, primary_key=True)
    driver_id = db.Column(db.Integer, db.ForeignKey('drivers.id'), nullable=False)
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    speed_kmh = db.Column(db.Float, default=0.0)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

class EmergencyReport(db.Model):
    __tablename__ = 'emergency_reports'
    id = db.Column(db.Integer, primary_key=True)
    emergency_id = db.Column(db.Integer, db.ForeignKey('emergencies.id'), nullable=False, unique=True)
    report_json = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class NotificationLog(db.Model):
    __tablename__ = 'notification_logs'
    id = db.Column(db.Integer, primary_key=True)
    emergency_id = db.Column(db.Integer)
    recipient_type = db.Column(db.String(50))
    recipient_id = db.Column(db.Integer)
    phone = db.Column(db.String(50))
    message = db.Column(db.Text)
    provider = db.Column(db.String(50))
    status = db.Column(db.String(50))
    provider_message_id = db.Column(db.String(100))
    error_message = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class CallLog(db.Model):
    __tablename__ = 'call_logs'
    id = db.Column(db.Integer, primary_key=True)
    emergency_id = db.Column(db.Integer)
    recipient_role = db.Column(db.String(50))
    phone = db.Column(db.String(50))
    status = db.Column(db.String(50))
    provider_call_id = db.Column(db.String(100))
    failure_reason = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)



class HospitalStaff(db.Model):
    __tablename__ = 'hospital_staff'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, unique=True)
    hospital_id = db.Column(db.Integer, db.ForeignKey('hospitals.id'), nullable=False)
    staff_role = db.Column(db.String(50), nullable=False) # doctor, nurse, receptionist, staff
    department = db.Column(db.String(100))
    specialization = db.Column(db.String(100))
    shift = db.Column(db.String(50))
    available = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class AmbulanceService(db.Model):
    __tablename__ = 'ambulance_services'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    owner_name = db.Column(db.String(150))
    phone = db.Column(db.String(50))
    email = db.Column(db.String(150))
    admin_user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Ambulance(db.Model):
    __tablename__ = 'ambulances'
    id = db.Column(db.Integer, primary_key=True)
    vehicle_number = db.Column(db.String(50), unique=True, nullable=False)
    ambulance_type = db.Column(db.String(50)) # ALS, BLS
    service_id = db.Column(db.Integer, db.ForeignKey('ambulance_services.id'), nullable=True)
    hospital_id = db.Column(db.Integer, db.ForeignKey('hospitals.id'), nullable=True) # if hospital owned
    driver_user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)
    status = db.Column(db.String(50), default='AVAILABLE') # AVAILABLE, DISPATCHED, EN_ROUTE, NEARBY, ARRIVED, UNAVAILABLE
    emergency_call_consent = db.Column(db.Boolean, default=False)
    emergency_call_enabled = db.Column(db.Boolean, default=False)
    phone_verified = db.Column(db.Boolean, default=False)
    preferred_language = db.Column(db.String(20), default='en')
    consent_timestamp = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class EmergencyEvent(db.Model):
    __tablename__ = 'emergency_events'
    id = db.Column(db.Integer, primary_key=True)
    driver_id = db.Column(db.Integer, db.ForeignKey('drivers.id'), nullable=False)
    emergency_type = db.Column(db.String(100))
    risk_level = db.Column(db.String(50)) # LOW, MEDIUM, HIGH, CRITICAL
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)
    status = db.Column(db.String(50), default='ACTIVE') # ACTIVE, DISPATCHED, IN_TRANSIT, ARRIVED, ADMITTED, RESOLVED
    assigned_hospital_id = db.Column(db.Integer, db.ForeignKey('hospitals.id'))
    assigned_ambulance_id = db.Column(db.Integer, db.ForeignKey('ambulances.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    resolved_at = db.Column(db.DateTime)

class EmergencyTimeline(db.Model):
    __tablename__ = 'emergency_timeline'
    id = db.Column(db.Integer, primary_key=True)
    emergency_id = db.Column(db.Integer, db.ForeignKey('emergency_events.id'), nullable=False)
    event_description = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

class HospitalAdmission(db.Model):
    __tablename__ = 'hospital_admissions'
    id = db.Column(db.Integer, primary_key=True)
    emergency_id = db.Column(db.Integer, db.ForeignKey('emergency_events.id'), nullable=True)
    hospital_id = db.Column(db.Integer, db.ForeignKey('hospitals.id'), nullable=False)
    patient_name = db.Column(db.String(150))
    age = db.Column(db.Integer)
    gender = db.Column(db.String(20))
    blood_group = db.Column(db.String(10))
    driver_id = db.Column(db.Integer, db.ForeignKey('drivers.id'), nullable=True)
    doctor_id = db.Column(db.Integer, db.ForeignKey('hospital_staff.id'))
    nurse_id = db.Column(db.Integer, db.ForeignKey('hospital_staff.id'))
    ward = db.Column(db.String(100))
    bed_number = db.Column(db.String(50))
    status = db.Column(db.String(50), default='ADMITTED') # ADMITTED, DISCHARGED
    admitted_at = db.Column(db.DateTime, default=datetime.utcnow)
    discharged_at = db.Column(db.DateTime)
    
    hospital = db.relationship('Hospital', backref='admissions', foreign_keys=[hospital_id])

class HealthReading(db.Model):
    __tablename__ = 'health_readings'
    id = db.Column(db.Integer, primary_key=True)
    driver_id = db.Column(db.Integer, db.ForeignKey('drivers.id'), nullable=False)
    heart_rate = db.Column(db.Float)
    spo2 = db.Column(db.Float)
    blood_pressure_sys = db.Column(db.Float)
    blood_pressure_dia = db.Column(db.Float)
    temperature = db.Column(db.Float)
    respiratory_rate = db.Column(db.Float)
    alcohol_level = db.Column(db.Float)
    stress_level = db.Column(db.Float)
    fatigue_level = db.Column(db.Float)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

class AuditLog(db.Model):
    __tablename__ = 'audit_logs'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    action = db.Column(db.String(255))
    details = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    ip_address = db.Column(db.String(50))

class ConsentAuditLog(db.Model):
    __tablename__ = 'consent_audit_logs'
    id = db.Column(db.Integer, primary_key=True)
    entity_id = db.Column(db.Integer, nullable=False)
    entity_type = db.Column(db.String(50), nullable=False) # Family, Hospital, Ambulance
    consent_type = db.Column(db.String(100), nullable=False)
    previous_value = db.Column(db.String(50))
    new_value = db.Column(db.String(50))
    changed_by = db.Column(db.String(150))
    reason = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

class CommunicationLog(db.Model):
    __tablename__ = 'communication_logs'
    id = db.Column(db.Integer, primary_key=True)
    emergency_id = db.Column(db.Integer)
    recipient_id = db.Column(db.Integer)
    recipient_type = db.Column(db.String(50))
    phone_number = db.Column(db.String(50))
    channel = db.Column(db.String(50)) # SMS, VOICE, EMAIL, DASHBOARD
    consent_status = db.Column(db.String(50))
    twilio_sid = db.Column(db.String(100))
    status = db.Column(db.String(50))
    error_code = db.Column(db.String(50))
    error_message = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

class VoiceInteraction(db.Model):
    __tablename__ = 'voice_interactions'
    id = db.Column(db.Integer, primary_key=True)
    driver_id = db.Column(db.Integer, db.ForeignKey('drivers.id'), nullable=False)
    input_text = db.Column(db.Text)
    intent = db.Column(db.String(100))
    detected_symptoms = db.Column(db.Text)
    risk_level = db.Column(db.String(50))
    ai_response = db.Column(db.Text)
    voice_language = db.Column(db.String(20), default='en-US')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Patient(db.Model):
    __tablename__ = 'patients'
    id = db.Column(db.Integer, primary_key=True)
    patient_id_code = db.Column(db.String(50), unique=True)
    hospital_id = db.Column(db.Integer, db.ForeignKey('hospitals.id'), nullable=False)
    driver_id = db.Column(db.Integer, db.ForeignKey('drivers.id'), nullable=True)
    driver_id_code = db.Column(db.String(50))
    name = db.Column(db.String(150), nullable=False)
    age = db.Column(db.Integer)
    gender = db.Column(db.String(20))
    blood_group = db.Column(db.String(10))
    phone = db.Column(db.String(50))
    emergency_contact = db.Column(db.String(100))
    previous_diseases = db.Column(db.Text)
    allergies = db.Column(db.Text)
    medical_history = db.Column(db.Text)
    current_status = db.Column(db.String(50), default='Admitted')
    bed_id = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class MedicalBill(db.Model):
    __tablename__ = 'medical_bills'
    id = db.Column(db.Integer, primary_key=True)
    bill_id_code = db.Column(db.String(50), unique=True, nullable=False)
    hospital_id = db.Column(db.Integer, db.ForeignKey('hospitals.id'), nullable=False)
    patient_id = db.Column(db.Integer, db.ForeignKey('patients.id'), nullable=False)
    emergency_id = db.Column(db.Integer, db.ForeignKey('emergencies.id'), nullable=True)
    admission_id = db.Column(db.Integer, db.ForeignKey('hospital_admissions.id'), nullable=True)
    doctor_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    patient_name = db.Column(db.String(150), nullable=False)
    admission_date = db.Column(db.String(50))
    discharge_date = db.Column(db.String(50))
    doctor_name = db.Column(db.String(150))
    diagnosis = db.Column(db.Text)
    treatment = db.Column(db.Text)
    consultation_fee = db.Column(db.Float, default=500.0)
    emergency_fee = db.Column(db.Float, default=1000.0)
    bed_charges = db.Column(db.Float, default=1500.0)
    icu_charges = db.Column(db.Float, default=0.0)
    lab_charges = db.Column(db.Float, default=500.0)
    ecg_charges = db.Column(db.Float, default=500.0)
    medicine_subtotal = db.Column(db.Float, default=0.0)
    other_charges = db.Column(db.Float, default=0.0)
    discount = db.Column(db.Float, default=0.0)
    tax_amount = db.Column(db.Float, default=0.0)
    grand_total = db.Column(db.Float, nullable=False)
    payment_status = db.Column(db.String(50), default='Pending')
    payment_method = db.Column(db.String(50), default='Cash')
    authorized_staff = db.Column(db.String(150))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class BillItem(db.Model):
    __tablename__ = 'bill_items'
    id = db.Column(db.Integer, primary_key=True)
    bill_id = db.Column(db.Integer, db.ForeignKey('medical_bills.id'), nullable=False)
    item_name = db.Column(db.String(150), nullable=False)
    category = db.Column(db.String(50), default='Medicine')
    quantity = db.Column(db.Integer, default=1)
    unit_price = db.Column(db.Float, nullable=False)
    total_price = db.Column(db.Float, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class PatientMedicalHistory(db.Model):
    __tablename__ = 'patient_medical_history'
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patients.id'), nullable=False)
    driver_id = db.Column(db.Integer, db.ForeignKey('drivers.id'), nullable=True)
    emergency_id = db.Column(db.Integer, db.ForeignKey('emergencies.id'), nullable=True)
    visit_date = db.Column(db.DateTime, default=datetime.utcnow)
    hospital_name = db.Column(db.String(200))
    doctor_name = db.Column(db.String(150))
    diagnosis = db.Column(db.Text)
    treatment = db.Column(db.Text)
    prescriptions_summary = db.Column(db.Text)
    report_id_code = db.Column(db.String(50))
    bill_id_code = db.Column(db.String(50))
    allergies = db.Column(db.Text)
    vitals_summary = db.Column(db.Text)
    admission_status = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

