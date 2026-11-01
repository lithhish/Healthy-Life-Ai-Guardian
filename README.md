# 🛡️ AI Driver Health Guardian

An industry-grade, professional AI-driven continuous health monitoring, emergency response, logistics dispatch, and longitudinal medical record system tailored for commercial and personal vehicle drivers.

The system acts as a smart wearable health monitoring platform, processing physiological vitals to detect severe emergency events, directing drivers via multi-lingual voice guidance, identifying nearest specialized hospitals, notifying linked family members, and dispatching ambulance vehicles.

---

## ✨ Key Features & Highlights

### 1. Monotonic Unique ID System
- **Drivers (`DRV-XXXXXX`)**: Permanent, monotonic IDs (`DRV-000001`, `DRV-000002`...) generated server-side. Never reset on server restarts and never reused.
- **Family Members (`FAM-XXXXXX`)**: Permanent family IDs (`FAM-000001`, `FAM-000002`...) linked directly to the driver's database ID and ID code.
- **Hospitals (`HOS-XXXXXX`)**: Permanent hospital identity (`HOS-000001`, `HOS-000002`...) attached to emergency services and staff logins.
- **Ambulance Drivers (`AMB-XXXXXX`)**: Permanent ambulance vehicle/driver IDs (`AMB-000001`, `AMB-000002`...) managing emergency dispatches.

### 2. Multi-Portal Ecosystem
- 🚗 **Driver Guardian Portal**: Live wearable vitals simulator, voice dictation, diagnostic risk prediction, and personal profile management.
- 👨‍👩‍👧 **Family Monitoring Portal**: Dynamic driver tracking, live emergency incident status, vitals logs, and linked driver identity.
- 🏥 **Hospital Staff Portal**: Patient reception, clinical history, ward admissions, billing management, and doctor/nurse assignment.
- 🏥 **Hospital Admin Portal**: Hospital profile management, bed capacity configuration, specialties verification, and staff registrations.
- 🚑 **Ambulance Portal**: Emergency dispatch alerts, GPS navigation, ETA estimation, and transport status toggling (`AVAILABLE`, `IN_TRANSIT`, `COMPLETED`).
- 🛡️ **Global Admin Command Center**: Live database counts, directory management, status toggles, and deletion safety checks across Drivers, Families, Hospitals, and Ambulances.

### 3. Decision Fusion AI Engine
- **Random Forest Classifier**: Multi-class risk analysis trained on physiological parameters.
- **Hard Physiological Threshold Overrides**:
  - **Hypoxia**: Triggered when $\text{SpO}_2 < 85\%$.
  - **Heart Attack**: Irregular HR ($> 120$ bpm) combined with chest pain symptoms.
  - **Hypertensive Crisis / Stroke**: Systolic BP $> 160$ mmHg with neurological symptoms.
- **NLP Symptom Matching**: TF-IDF semantic symptom matching for clinical diagnostics.

### 4. Longitudinal Driver Medical History & Reports
- **Complete Longitudinal Record**: Unifies clinical visits, hospital admissions, prescriptions, device health logs, uploaded medical documents, and emergency incidents.
- **Server-Side PDF Generator**: Compiles clinical event logs and vitals graphs into downloadable PDF Medical Reports.
- **Role-Based Access Control (RBAC)**: Strict server-side security checks (`403 Forbidden` on unauthorized cross-patient data access).

---

## 💻 Terminal Commands to Run the Project

### Option A: Standard PowerShell / Command Prompt Setup

#### 1. Open Terminal & Navigate to Project Folder
```powershell
cd "c:\Users\rslit\Downloads\Ai with Healthy Life Ai Guardian"
```

#### 2. Create Python Virtual Environment (If not already created)
```powershell
python -m venv .venv
```

#### 3. Activate Virtual Environment
- **Windows (PowerShell)**:
  ```powershell
  .\.venv\Scripts\Activate.ps1
  ```
- **Windows (Command Prompt / CMD)**:
  ```cmd
  .venv\Scripts\activate.bat
  ```
- **Linux / macOS**:
  ```bash
  source .venv/bin/activate
  ```

#### 4. Install Dependencies
```powershell
pip install -r requirements.txt
```

#### 5. Initialize Database & Seed Data
```powershell
python -c "from database import init_db; init_db()"
```

#### 6. Run the Flask Application Server
```powershell
python app.py
```
*(The server will start at `http://127.0.0.1:5000`)*

---

### Option B: Run Automated Verification & Flow Test Suites

Run the comprehensive unit and integration test suites:

#### 1. Master System Verification Suite
```powershell
.venv\Scripts\python.exe scratch\test_master_verification.py
```

#### 2. Master Flow Test Suite (Driver IDs, Family Mapping & Admin APIs)
```powershell
.venv\Scripts\python.exe scratch\test_master_flow.py
```

---

## 🔑 Demo Access Credentials & Portals

| Portal | URL Path | Demo Username | Demo Password | Role |
|---|---|---|---|---|
| **Portal Hub** | `/login/hub` | -- | -- | Central Hub |
| **Driver Portal** | `/driver/login` | `driver1` | `password123` | Driver |
| **Family Portal** | `/family/login` | `family1` | `password123` | Family |
| **Hospital Staff** | `/staff/login` | `doctor1` | `password123` | Doctor / Nurse / Staff |
| **Hospital Admin** | `/hospital/login` | `hospital1` | `password123` | Hospital Admin |
| **Ambulance Portal** | `/ambulance/login` | `ambulance1` | `password123` | Ambulance Driver |
| **Global Admin** | `/admin/login` | `admin1` | `password123` | Admin |

---

## 📂 Project Architecture

```text
Ai with Healthy Life Ai Guardian/
├── app.py                      # Flask Application Server & SocketIO runner
├── database.py                 # SQLite Schema Initialization, Monotonic ID Engines & Seeding
├── ai_engine.py                # Random Forest & NLP Clinical Diagnostic Engine
├── report_generator.py         # ReportLab PDF Emergency Report Compiler
├── requirements.txt            # Project dependencies
├── models/                     # SQLAlchemy Models (User, Driver, Family, Hospital, Ambulance)
├── routes/                     # Blueprint Route Handlers
│   ├── auth.py                 # Multi-Portal Authentication & Role Access
│   ├── main.py                 # Registration Pages, Driver & Family Dashboards
│   ├── api.py                  # Vitals Simulation, Verification, Longitudinal History & PDF APIs
│   ├── admin.py                # Admin Directory Management & Analytics APIs
│   ├── hospital.py             # Hospital Staff, Doctor & Billing APIs
│   └── ambulance.py            # Ambulance Dispatch & Tracking APIs
├── templates/                  # Jinja2 HTML5 UI Templates
│   ├── base.html               # Unified Left Sidebar & Aesthetics
│   ├── driver_dashboard.html   # Driver Command Center & Vitals Simulator
│   ├── family_dashboard.html   # Family Monitoring & Emergency Tracking
│   ├── admin_dashboard.html    # Global Admin Command Portal
│   ├── hospital_dashboard.html # Hospital Staff Command Center
│   └── ambulance_dashboard.html# Ambulance Dispatch Tracker
└── scratch/                    # Test Verification Scripts
    ├── test_master_verification.py
    └── test_master_flow.py
```

---

## 🧪 Acceptance & Quality Checklist

- [x] Monotonic unique Driver IDs (`DRV-000001`, `DRV-000002`...) generated server-side.
- [x] Dynamic family linkage validating exact entered Driver ID against database.
- [x] Family Dashboard dynamically loading linked driver data (zero hardcoded fallbacks).
- [x] Monotonic ID system for Hospitals (`HOS-XXXXXX`), Family (`FAM-XXXXXX`), and Ambulances (`AMB-XXXXXX`).
- [x] Global Admin Dashboard with live database counts and search/filter management tables.
- [x] Longitudinal Driver Medical Record API and server-side PDF Emergency Report downloading.
- [x] 100% test pass rate across all automated test suites.
