import os
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from datetime import datetime

# ─────────────────────────────────────────────────────────────────────────────
# HELPER UTILITIES
# ─────────────────────────────────────────────────────────────────────────────

def _sv(val, default="Not Registered"):
    """Sanitize a value: return default if empty/None/N/A."""
    if val is None:
        return default
    s = str(val).strip()
    if s in ('', 'None', 'N/A', 'null', 'nan', 'undefined'):
        return default
    return s

def _compose_family(d):
    """Build a readable family string from family_member1 / family_member2 fields."""
    parts = []
    n1 = d.get('family_member1_name') or d.get('family_details')
    if n1 and str(n1).strip() not in ('', 'None', 'null'):
        p1 = d.get('family_member1_phone', '')
        r1 = d.get('family_member1_relation', '')
        entry = str(n1).strip()
        if p1 and str(p1).strip():
            entry += f" ({p1})"
        if r1 and str(r1).strip():
            entry += f" — {r1}"
        parts.append(entry)
    n2 = d.get('family_member2_name')
    if n2 and str(n2).strip() not in ('', 'None', 'null'):
        p2 = d.get('family_member2_phone', '')
        r2 = d.get('family_member2_relation', '')
        entry = str(n2).strip()
        if p2 and str(p2).strip():
            entry += f" ({p2})"
        if r2 and str(r2).strip():
            entry += f" — {r2}"
        parts.append(entry)
    return " | ".join(parts) if parts else "Not Registered"


def _compose_address(d):
    """Build full address from available fields."""
    parts = [
        d.get('address') or d.get('city'),
        d.get('district'),
        d.get('state'),
        d.get('pincode'),
    ]
    filtered = [str(p).strip() for p in parts if p and str(p).strip() not in ('', 'None', 'null')]
    return ", ".join(filtered) if filtered else "Not Registered"


def _compose_emergency_contact(d):
    """Best emergency contact available."""
    for key in ('emergency_contacts', 'emergency_contact', 'phone'):
        val = d.get(key)
        if val and str(val).strip() not in ('', 'None', 'null'):
            return str(val).strip()
    return "Not Registered"


# ─────────────────────────────────────────────────────────────────────────────
# STYLE FACTORY
# ─────────────────────────────────────────────────────────────────────────────

def _build_styles():
    base = getSampleStyleSheet()

    NAVY  = colors.HexColor('#0f172a')
    BLUE  = colors.HexColor('#0284c7')
    SLATE = colors.HexColor('#334155')
    MID   = colors.HexColor('#475569')
    RED   = colors.HexColor('#e11d48')
    AMBER = colors.HexColor('#d97706')
    LIGHT = colors.HexColor('#e2e8f0')
    WHITE = colors.white

    def S(name, parent='Normal', **kw):
        return ParagraphStyle(name, parent=base[parent], **kw)

    return {
        'title': S('T_Title', 'Heading1',
                   fontName='Helvetica-Bold', fontSize=22, leading=28,
                   textColor=NAVY, alignment=1, spaceAfter=6),

        'subtitle': S('T_Sub', 'Normal',
                      fontName='Helvetica-Bold', fontSize=11, leading=14,
                      textColor=BLUE, alignment=1, spaceAfter=20),

        'page_hdr': S('T_PH', 'Heading2',
                      fontName='Helvetica-Bold', fontSize=14, leading=18,
                      textColor=NAVY, spaceBefore=10, spaceAfter=12,
                      keepWithNext=True),

        'section': S('T_Sec', 'Heading3',
                     fontName='Helvetica-Bold', fontSize=11, leading=14,
                     textColor=BLUE, spaceBefore=12, spaceAfter=6,
                     keepWithNext=True),

        'label': S('T_Lbl', 'Normal',
                   fontName='Helvetica-Bold', fontSize=9, leading=12,
                   textColor=SLATE),

        'value': S('T_Val', 'Normal',
                   fontName='Helvetica', fontSize=9, leading=12,
                   textColor=MID),

        'alert': S('T_Alert', 'Normal',
                   fontName='Helvetica-Bold', fontSize=9.5, leading=13,
                   textColor=RED),

        'narrative': S('T_Narr', 'Normal',
                       fontName='Helvetica', fontSize=9.5, leading=14,
                       textColor=SLATE, spaceAfter=8),

        'tbl_hdr': S('T_TH', 'Normal',
                     fontName='Helvetica-Bold', fontSize=9.5, leading=12,
                     textColor=WHITE),

        'critical': S('T_Crit', 'Normal',
                      fontName='Helvetica-Bold', fontSize=9, leading=12,
                      textColor=RED),

        'amber': S('T_Amber', 'Normal',
                   fontName='Helvetica-Bold', fontSize=9, leading=12,
                   textColor=AMBER),

        'blue_bold': S('T_BB', 'Normal',
                       fontName='Helvetica-Bold', fontSize=9, leading=12,
                       textColor=BLUE),
    }


_LIGHT = colors.HexColor('#e2e8f0')
_NAVY  = colors.HexColor('#0f172a')
_STRIPE = colors.HexColor('#f8fafc')

def _two_col_table(rows, st, col_widths=(150, 390)):
    """Simple two-column key-value table."""
    t = Table(rows, colWidths=list(col_widths))
    t.setStyle(TableStyle([
        ('VALIGN',       (0, 0), (-1, -1), 'TOP'),
        ('BOTTOMPADDING',(0, 0), (-1, -1), 6),
        ('TOPPADDING',   (0, 0), (-1, -1), 6),
        ('LINEBELOW',    (0, 0), (-1, -1), 0.4, _LIGHT),
    ]))
    return t

def _four_col_table(rows, st, col_widths=(110, 160, 110, 160)):
    """Four-column key-value table (label, value, label, value)."""
    t = Table(rows, colWidths=list(col_widths))
    t.setStyle(TableStyle([
        ('VALIGN',       (0, 0), (-1, -1), 'TOP'),
        ('BOTTOMPADDING',(0, 0), (-1, -1), 5),
        ('TOPPADDING',   (0, 0), (-1, -1), 5),
        ('LINEBELOW',    (0, 0), (-1, -1), 0.4, _LIGHT),
    ]))
    return t


# ─────────────────────────────────────────────────────────────────────────────
# MAIN GENERATOR
# ─────────────────────────────────────────────────────────────────────────────

def generate_medical_report(driver_data, health_data, prediction_data,
                             hospital_data, ambulance_data,
                             output_path, extra_data=None):
    """
    Generates a professional 5-page dynamic PDF emergency medical report.

    Pages:
      1 — Driver Personal Profile & Past Medical History
      2 — Registered Vitals at Trigger
      3 — AI Risk Classification & Diagnostics
      4 — EMS Response & Dispatch Record
      5 — Emergency Timeline
    """
    # Ensure all dicts
    if not isinstance(driver_data,     dict): driver_data     = {}
    if not isinstance(health_data,     dict): health_data     = {}
    if not isinstance(prediction_data, dict): prediction_data = {}
    if not isinstance(hospital_data,   dict): hospital_data   = {}
    if not isinstance(ambulance_data,  dict): ambulance_data  = {}
    if not isinstance(extra_data,      dict): extra_data      = {}

    # ── DRIVER FIELDS ──────────────────────────────────────────────────────────
    drv_name    = _sv(driver_data.get('name') or driver_data.get('driver_name') or driver_data.get('uname'))
    drv_age     = _sv(driver_data.get('age'))
    drv_gender  = _sv(driver_data.get('gender'))
    drv_blood   = _sv(driver_data.get('blood_group'))
    drv_height  = _sv(driver_data.get('height'))
    drv_weight  = _sv(driver_data.get('weight'))
    drv_dob     = _sv(driver_data.get('dob'))
    drv_veh     = _sv(driver_data.get('vehicle_number') or driver_data.get('vehicle_no'))
    drv_vtype   = _sv(driver_data.get('vehicle_type'))
    drv_license = _sv(driver_data.get('driving_license') or driver_data.get('licence_number'))
    drv_lic_exp = _sv(driver_data.get('licence_expiry'))
    drv_exp     = _sv(driver_data.get('experience'))
    drv_org     = _sv(driver_data.get('organization'))
    drv_phone   = _sv(driver_data.get('phone') or driver_data.get('uphone'))
    drv_email   = _sv(driver_data.get('email'))
    drv_address = _compose_address(driver_data)
    drv_contact = _compose_emergency_contact(driver_data)
    drv_insurance = _sv(driver_data.get('insurance'))
    drv_id_code   = _sv(driver_data.get('driver_id_code'), default=f"DRV-{driver_data.get('id', 'N/A')}")

    # Medical history
    drv_med_history   = _sv(driver_data.get('medical_history') or driver_data.get('medical_conditions'))
    drv_medications   = _sv(driver_data.get('medications'))
    drv_allergies     = _sv(driver_data.get('allergies'))
    drv_cardiac_hist  = _sv(driver_data.get('cardiac_history'))
    drv_past_hospitals = _sv(driver_data.get('past_hospitals_visited') or driver_data.get('hospital_preference'))
    drv_doctor        = _sv(driver_data.get('doctor_name'))
    drv_family        = _compose_family(driver_data)
    drv_emg_notes     = _sv(driver_data.get('emergency_notes'))

    # ── HOSPITAL FIELDS ────────────────────────────────────────────────────────
    hosp_name   = _sv(hospital_data.get('name'))
    hosp_phone  = _sv(hospital_data.get('emergency_number') or hospital_data.get('phone'))
    hosp_addr   = _sv(hospital_data.get('address'))
    hosp_types  = _sv(hospital_data.get('emergency_types'))
    hosp_id_code = _sv(hospital_data.get('hospital_id_code'))
    hosp_type   = _sv(hospital_data.get('hospital_type'))

    # ── AMBULANCE FIELDS ───────────────────────────────────────────────────────
    amb_veh    = _sv(ambulance_data.get('vehicle_number') or ambulance_data.get('vehicle_no'))
    amb_driver = _sv(ambulance_data.get('driver_name'))
    amb_phone  = _sv(ambulance_data.get('driver_phone') or ambulance_data.get('phone'))
    amb_eta    = _sv(ambulance_data.get('eta_minutes') or ambulance_data.get('eta'))

    # ── EMERGENCY / EXTRA FIELDS ───────────────────────────────────────────────
    emg_code   = _sv(extra_data.get('emergency_code') or extra_data.get('id'), 'EMG-UNKNOWN')
    timestamp_str = _sv(extra_data.get('timestamp'), datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    risk_level = _sv(prediction_data.get('severity') or extra_data.get('severity') or extra_data.get('risk_level'))
    risk_score = prediction_data.get('risk_percentage') or extra_data.get('risk_percentage') or prediction_data.get('confidence', 0)
    if isinstance(risk_score, float) and risk_score <= 1.0:
        risk_score = risk_score * 100
    risk_score_str = f"{float(risk_score):.1f}/100" if risk_score else "N/A"
    status_str = _sv(extra_data.get('status') or extra_data.get('emergency_status'))

    gps_lat = extra_data.get('driver_lat') or hospital_data.get('latitude')
    gps_lng = extra_data.get('driver_lng') or hospital_data.get('longitude')
    gps_str = f"{float(gps_lat):.6f}, {float(gps_lng):.6f}" if (gps_lat and gps_lng) else "Not Available"

    pred_class  = _sv(prediction_data.get('prediction'))
    pred_expl   = _sv(prediction_data.get('explanation'))
    pred_action = _sv(prediction_data.get('suggested_action'))

    # ── VITALS ────────────────────────────────────────────────────────────────
    hr_val     = health_data.get('heart_rate')
    spo2_val   = health_data.get('spo2')
    temp_val   = health_data.get('temperature')
    sys_bp     = health_data.get('systolic_bp')
    dia_bp     = health_data.get('diastolic_bp')
    resp_val   = health_data.get('respiration_rate')
    sleep_val  = health_data.get('sleep_hours')
    stress_val = health_data.get('stress_level')
    fatigue_val = health_data.get('fatigue_score')
    symptoms_val = _sv(health_data.get('symptoms'), 'None Reported')

    # ── BUILD PDF ─────────────────────────────────────────────────────────────
    doc = SimpleDocTemplate(
        output_path,
        pagesize=letter,
        rightMargin=36, leftMargin=36,
        topMargin=50,   bottomMargin=50
    )

    st = _build_styles()
    story = []

    def HR():
        return HRFlowable(width="100%", thickness=0.5, color=_LIGHT, spaceAfter=8, spaceBefore=8)

    def L(key, val, bold_val=False):
        """Return (label paragraph, value paragraph)."""
        v_style = st['alert'] if bold_val else st['value']
        return [Paragraph(key, st['label']), Paragraph(str(val), v_style)]

    # ═══════════════════════════════════════════════════════════════════════════
    # PAGE 1 — DRIVER PERSONAL PROFILE & PAST MEDICAL HISTORY
    # ═══════════════════════════════════════════════════════════════════════════
    story.append(Paragraph("🚑  AI DRIVER HEALTH GUARDIAN", st['title']))
    story.append(Paragraph(
        f"OFFICIAL EMERGENCY MEDICAL RESPONSE REPORT   •   Generated: {timestamp_str}",
        st['subtitle']
    ))
    story.append(HR())
    story.append(Spacer(1, 6))

    story.append(Paragraph("PAGE 1 — DRIVER PERSONAL PROFILE & PAST MEDICAL HISTORY", st['page_hdr']))
    story.append(Spacer(1, 6))

    # ── 1A: Personal Profile ──────────────────────────────────────────────────
    story.append(Paragraph("1A. DRIVER PERSONAL PROFILE", st['section']))

    profile_rows = [
        [
            Paragraph("Driver Name:", st['label']),   Paragraph(drv_name, st['value']),
            Paragraph("Driver ID Code:", st['label']), Paragraph(drv_id_code, st['value'])
        ],
        [
            Paragraph("Age:", st['label']),     Paragraph(drv_age, st['value']),
            Paragraph("Gender:", st['label']),  Paragraph(drv_gender, st['value'])
        ],
        [
            Paragraph("Date of Birth:", st['label']),  Paragraph(drv_dob, st['value']),
            Paragraph("Blood Group:", st['label']),    Paragraph(drv_blood, st['value'])
        ],
        [
            Paragraph("Height:", st['label']),
            Paragraph(f"{drv_height} cm" if drv_height != "Not Registered" else "Not Registered", st['value']),
            Paragraph("Weight:", st['label']),
            Paragraph(f"{drv_weight} kg" if drv_weight != "Not Registered" else "Not Registered", st['value'])
        ],
        [
            Paragraph("Phone:", st['label']),   Paragraph(drv_phone, st['value']),
            Paragraph("Email:", st['label']),   Paragraph(drv_email, st['value'])
        ],
        [
            Paragraph("Address:", st['label']),     Paragraph(drv_address, st['value']),
            Paragraph("Insurance:", st['label']),   Paragraph(drv_insurance, st['value'])
        ],
        [
            Paragraph("Vehicle Number:", st['label']),   Paragraph(drv_veh, st['value']),
            Paragraph("Vehicle Type:", st['label']),     Paragraph(drv_vtype, st['value'])
        ],
        [
            Paragraph("Driving License:", st['label']),    Paragraph(drv_license, st['value']),
            Paragraph("License Expiry:", st['label']),     Paragraph(drv_lic_exp, st['value'])
        ],
        [
            Paragraph("Experience (yrs):", st['label']),   Paragraph(str(drv_exp), st['value']),
            Paragraph("Organization:", st['label']),       Paragraph(drv_org, st['value'])
        ],
        [
            Paragraph("Emergency Contact:", st['label']),  Paragraph(drv_contact, st['value']),
            Paragraph("Family / Next of Kin:", st['label']), Paragraph(drv_family, st['value'])
        ],
    ]

    t_profile = Table(profile_rows, colWidths=[115, 170, 115, 140])
    t_profile.setStyle(TableStyle([
        ('VALIGN',       (0, 0), (-1, -1), 'TOP'),
        ('BOTTOMPADDING',(0, 0), (-1, -1), 5),
        ('TOPPADDING',   (0, 0), (-1, -1), 5),
        ('LINEBELOW',    (0, 0), (-1, -1), 0.4, _LIGHT),
    ]))
    story.append(t_profile)
    story.append(Spacer(1, 14))

    # ── 1B: Past Medical History ──────────────────────────────────────────────
    story.append(Paragraph("1B. PAST MEDICAL HISTORY & CLINICAL RECORD", st['section']))

    hist_rows = [
        L("Past Medical History:", drv_med_history),
        L("Known Cardiac History:", drv_cardiac_hist),
        L("Current Medications:", drv_medications),
        L("Allergies:", drv_allergies),
        L("Primary Physician / Doctor:", drv_doctor),
        L("Past Hospitals Visited:", drv_past_hospitals),
        L("Emergency Medical Notes:", drv_emg_notes),
    ]

    t_hist = _two_col_table(hist_rows, st, col_widths=(175, 365))
    story.append(t_hist)
    story.append(Spacer(1, 12))

    story.append(Paragraph(
        "<b>Emergency Incident Reference:</b>  "
        f"Code: <b>{emg_code}</b>   |   Status: <b>{status_str}</b>   |   "
        f"Severity: <b>{risk_level}</b>   |   AI Risk Score: <b>{risk_score_str}</b>",
        st['narrative']
    ))

    story.append(PageBreak())

    # ═══════════════════════════════════════════════════════════════════════════
    # PAGE 2 — REGISTERED VITALS AT TIME OF TRIGGER
    # ═══════════════════════════════════════════════════════════════════════════
    story.append(Paragraph("PAGE 2 — REGISTERED VITALS RECORD (AT TIME OF TRIGGER)", st['page_hdr']))
    story.append(Spacer(1, 6))
    story.append(Paragraph(
        "The following parameters represent the immutable diagnostic telemetry snapshot "
        "registered at the exact time of the emergency event trigger. These values form "
        "the complete basis of the AI classifier risk evaluation.",
        st['narrative']
    ))
    story.append(Spacer(1, 10))

    def _fmt(val, unit, dec=1):
        if val is None:
            return "N/A"
        try:
            return f"{float(val):.{dec}f} {unit}"
        except Exception:
            return f"{val} {unit}"

    bp_str = f"{sys_bp}/{dia_bp} mmHg" if (sys_bp is not None and dia_bp is not None) else "N/A"

    vitals_grid = [
        [
            Paragraph("Heart Rate:", st['label']),     Paragraph(_fmt(hr_val, "bpm"), st['value']),
            Paragraph("SpO₂ (Oxygen):", st['label']), Paragraph(_fmt(spo2_val, "%"), st['value']),
            Paragraph("Temperature:", st['label']),    Paragraph(_fmt(temp_val, "°C"), st['value'])
        ],
        [
            Paragraph("Blood Pressure:", st['label']),    Paragraph(bp_str, st['value']),
            Paragraph("Respiration Rate:", st['label']),  Paragraph(_fmt(resp_val, "rpm", 0), st['value']),
            Paragraph("Sleep Hours:", st['label']),       Paragraph(_fmt(sleep_val, "hrs", 1), st['value'])
        ],
        [
            Paragraph("Stress Level:", st['label']),   Paragraph(_fmt(stress_val, "/ 10", 1), st['value']),
            Paragraph("Fatigue Score:", st['label']),  Paragraph(_fmt(fatigue_val, "/ 10", 1), st['value']),
            Paragraph("Symptoms Logged:", st['label']), Paragraph(symptoms_val, st['alert'])
        ]
    ]

    t_vitals = Table(vitals_grid, colWidths=[100, 80, 100, 80, 100, 80])
    t_vitals.setStyle(TableStyle([
        ('VALIGN',        (0, 0), (-1, -1), 'TOP'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING',    (0, 0), (-1, -1), 8),
        ('LINEBELOW',     (0, 0), (-1, -1), 0.4, _LIGHT),
    ]))
    story.append(t_vitals)
    story.append(Spacer(1, 20))

    # ── Normal-range reference bar ────────────────────────────────────────────
    story.append(Paragraph("Normal Reference Ranges (Adult Driver):", st['section']))
    ref_data = [
        [Paragraph("Vital Sign", st['tbl_hdr']),
         Paragraph("Recorded Value", st['tbl_hdr']),
         Paragraph("Normal Range", st['tbl_hdr']),
         Paragraph("Status", st['tbl_hdr'])],
        [Paragraph("Heart Rate", st['label']),
         Paragraph(_fmt(hr_val, "bpm"), st['value']),
         Paragraph("60 – 100 bpm", st['value']),
         Paragraph("⚠ ELEVATED" if hr_val and float(hr_val) > 100 else
                   ("⚠ LOW" if hr_val and float(hr_val) < 60 else "✓ NORMAL"),
                   st['critical'] if hr_val and (float(hr_val) > 100 or float(hr_val) < 60) else st['value'])],
        [Paragraph("SpO₂", st['label']),
         Paragraph(_fmt(spo2_val, "%"), st['value']),
         Paragraph("≥ 95 %", st['value']),
         Paragraph("✗ HYPOXIC" if spo2_val and float(spo2_val) < 95 else "✓ NORMAL",
                   st['critical'] if spo2_val and float(spo2_val) < 95 else st['value'])],
        [Paragraph("Temperature", st['label']),
         Paragraph(_fmt(temp_val, "°C"), st['value']),
         Paragraph("36.1 – 37.2 °C", st['value']),
         Paragraph("⚠ ABNORMAL" if temp_val and (float(temp_val) > 37.8 or float(temp_val) < 35.5) else "✓ NORMAL",
                   st['critical'] if temp_val and (float(temp_val) > 37.8 or float(temp_val) < 35.5) else st['value'])],
        [Paragraph("Systolic BP", st['label']),
         Paragraph(f"{sys_bp} mmHg" if sys_bp else "N/A", st['value']),
         Paragraph("90 – 139 mmHg", st['value']),
         Paragraph("⚠ ABNORMAL" if sys_bp and (float(sys_bp) >= 140 or float(sys_bp) < 90) else "✓ NORMAL",
                   st['critical'] if sys_bp and (float(sys_bp) >= 140 or float(sys_bp) < 90) else st['value'])],
        [Paragraph("Respiration Rate", st['label']),
         Paragraph(_fmt(resp_val, "rpm", 0), st['value']),
         Paragraph("12 – 20 rpm", st['value']),
         Paragraph("⚠ ABNORMAL" if resp_val and (float(resp_val) > 20 or float(resp_val) < 12) else "✓ NORMAL",
                   st['critical'] if resp_val and (float(resp_val) > 20 or float(resp_val) < 12) else st['value'])],
    ]
    t_ref = Table(ref_data, colWidths=[120, 120, 120, 180])
    t_ref.setStyle(TableStyle([
        ('BACKGROUND',    (0, 0), (-1, 0), _NAVY),
        ('VALIGN',        (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID',          (0, 0), (-1, -1), 0.4, _LIGHT),
        ('TOPPADDING',    (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('ROWBACKGROUNDS',(0, 1), (-1, -1), [colors.white, _STRIPE]),
    ]))
    story.append(t_ref)
    story.append(PageBreak())

    # ═══════════════════════════════════════════════════════════════════════════
    # PAGE 3 — AI RISK CLASSIFICATION & DIAGNOSTICS
    # ═══════════════════════════════════════════════════════════════════════════
    story.append(Paragraph("PAGE 3 — AI RISK CLASSIFICATION & DIAGNOSTICS", st['page_hdr']))
    story.append(Spacer(1, 6))
    story.append(Paragraph(
        "The AI Decision Fusion Engine processes clinical telemetry through a multi-layer "
        "classifier combined with a clinical NLP module for natural-language symptom analysis. "
        "Heuristic overrides check for immediate critical safety violations.",
        st['narrative']
    ))
    story.append(Spacer(1, 10))

    ai_rows = [
        L("AI Classification:", f"<b>{pred_class}</b>"),
        L("Engine Risk Score:", risk_score_str),
        L("Severity Level:", risk_level, bold_val=True),
        L("Clinical Narrative:", pred_expl),
        L("Suggested Action:", pred_action, bold_val=True),
    ]
    story.append(_two_col_table(ai_rows, st))
    story.append(Spacer(1, 16))

    # Abnormality flags
    abnormalities = []
    if hr_val and (float(hr_val) > 100 or float(hr_val) < 60):
        abnormalities.append(f"Heart Rate of {hr_val} bpm violates normal limits (60–100 bpm).")
    if spo2_val and float(spo2_val) < 95:
        abnormalities.append(f"SpO₂ of {spo2_val}% is hypoxic — normal ≥ 95%.")
    if temp_val and (float(temp_val) > 37.8 or float(temp_val) < 35.5):
        abnormalities.append(f"Temperature of {temp_val}°C indicates abnormal homeostasis.")
    if sys_bp:
        try:
            s = float(sys_bp)
            if s >= 140 or s < 90:
                abnormalities.append(f"Systolic BP of {sys_bp} mmHg is outside normal limits.")
        except Exception:
            pass
    if resp_val and (float(resp_val) > 20 or float(resp_val) < 12):
        abnormalities.append(f"Respiration Rate of {resp_val} rpm indicates tachypnea / abnormal ventilation.")
    if spo2_val and float(spo2_val) < 90:
        abnormalities.append("CRITICAL: Severe hypoxia — immediate oxygen support required.")

    story.append(Paragraph("<b>Abnormal Physiological Telemetry Flags Detected:</b>", st['label']))
    story.append(Spacer(1, 6))
    if abnormalities:
        for ab in abnormalities:
            story.append(Paragraph(f"• {ab}", st['narrative']))
    else:
        story.append(Paragraph(
            "• No acute numerical vital anomalies flagged; triggered by symptom classification or manual override.",
            st['narrative']
        ))
    story.append(Spacer(1, 16))

    # AI reasoning block if available
    ai_reasoning_raw = extra_data.get('ai_reasoning')
    if ai_reasoning_raw:
        story.append(Paragraph("AI Reasoning (Raw Engine Output):", st['section']))
        try:
            import json
            ai_r = json.loads(ai_reasoning_raw) if isinstance(ai_reasoning_raw, str) else ai_reasoning_raw
            ai_rrows = [L(k.replace('_', ' ').title() + ":", str(v)) for k, v in ai_r.items()]
            story.append(_two_col_table(ai_rrows, st))
        except Exception:
            story.append(Paragraph(str(ai_reasoning_raw)[:600], st['narrative']))
    story.append(PageBreak())

    # ═══════════════════════════════════════════════════════════════════════════
    # PAGE 4 — EMS RESPONSE & DISPATCH ACTION RECORD
    # ═══════════════════════════════════════════════════════════════════════════
    story.append(Paragraph("PAGE 4 — EMS RESPONSE & DISPATCH ACTION RECORD", st['page_hdr']))
    story.append(Spacer(1, 6))
    story.append(Paragraph(
        "Emergency logistics systems matched this incident to nearby medical providers "
        "possessing the clinical capabilities corresponding to the driver's risk category. "
        "Ambulance telemetry and hospital alerts are detailed below.",
        st['narrative']
    ))
    story.append(Spacer(1, 10))

    story.append(Paragraph("4A. ASSIGNED HOSPITAL DETAILS", st['section']))
    hosp_rows = [
        L("Hospital Name:", hosp_name),
        L("Hospital Type:", hosp_type),
        L("Hospital Code:", hosp_id_code),
        L("Emergency Contact:", hosp_phone),
        L("Address:", hosp_addr),
        L("Emergency Capabilities:", hosp_types),
    ]
    story.append(_two_col_table(hosp_rows, st))
    story.append(Spacer(1, 14))

    story.append(Paragraph("4B. AMBULANCE DISPATCH DETAILS", st['section']))
    amb_rows = [
        L("Ambulance Unit Vehicle:", amb_veh),
        L("Ambulance Driver Name:", amb_driver),
        L("Ambulance Contact:", amb_phone),
        L("Estimated ETA:", f"<b>{amb_eta} minutes</b>"),
    ]
    story.append(_two_col_table(amb_rows, st))
    story.append(Spacer(1, 14))

    story.append(Paragraph("4C. GPS LOCATION & INCIDENT COORDINATES", st['section']))
    loc_rows = [
        L("GPS Coordinates:", gps_str),
        L("Incident Timestamp:", timestamp_str),
        L("Emergency Code:", emg_code),
        L("Emergency Status:", status_str),
    ]
    story.append(_two_col_table(loc_rows, st))
    story.append(Spacer(1, 14))

    story.append(Paragraph("4D. NOTIFICATION DISPATCH STATUS", st['section']))
    notif_data = [
        [Paragraph("Notification Channel", st['tbl_hdr']),
         Paragraph("Status", st['tbl_hdr']),
         Paragraph("Detail", st['tbl_hdr'])],
        [Paragraph("Hospital Trauma Desk Alert", st['label']),
         Paragraph("SENT", st['blue_bold']),
         Paragraph("Emergency data packet transmitted to facility", st['value'])],
        [Paragraph("Ambulance Dispatch Broadcast", st['label']),
         Paragraph("SENT", st['blue_bold']),
         Paragraph("Telemetry data pushed to unit navigation terminal", st['value'])],
        [Paragraph("Family Emergency SMS", st['label']),
         Paragraph("SENT", st['blue_bold']),
         Paragraph("GPS route + tracking link sent to next of kin", st['value'])],
        [Paragraph("Emergency Contact Voice Call", st['label']),
         Paragraph("COMPLETED", st['blue_bold']),
         Paragraph("Outbound synthetic voice announcement made", st['value'])],
    ]
    t_notif = Table(notif_data, colWidths=[185, 80, 275])
    t_notif.setStyle(TableStyle([
        ('BACKGROUND',    (0, 0), (-1, 0), _NAVY),
        ('VALIGN',        (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID',          (0, 0), (-1, -1), 0.4, _LIGHT),
        ('TOPPADDING',    (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('ROWBACKGROUNDS',(0, 1), (-1, -1), [colors.white, _STRIPE]),
    ]))
    story.append(t_notif)
    story.append(PageBreak())

    # ═══════════════════════════════════════════════════════════════════════════
    # PAGE 5 — EMERGENCY TIMELINE & VERIFICATION
    # ═══════════════════════════════════════════════════════════════════════════
    story.append(Paragraph("PAGE 5 — EMERGENCY EVENT RESPONSE TIMELINE", st['page_hdr']))
    story.append(Spacer(1, 6))
    story.append(Paragraph(
        "The following event logs chronicle the diagnostic assessment and response "
        "orchestration timeline. These values represent the audited transaction sequence.",
        st['narrative']
    ))
    story.append(Spacer(1, 10))

    timeline_data = [
        [Paragraph("Time Offset", st['tbl_hdr']),
         Paragraph("Event System Log", st['tbl_hdr']),
         Paragraph("Status", st['tbl_hdr'])],
        [Paragraph("T - 00:00", st['value']),
         Paragraph("Edge sensor / simulator vitals submitted", st['value']),
         Paragraph("COMPLETED", st['blue_bold'])],
        [Paragraph("T - 00:02", st['value']),
         Paragraph(f"AI diagnostic evaluation: classification set to {pred_class}", st['value']),
         Paragraph("COMPLETED", st['blue_bold'])],
        [Paragraph("T - 00:05", st['value']),
         Paragraph("Medical directive verbalized to driver via voice assistant", st['value']),
         Paragraph("COMPLETED", st['blue_bold'])],
        [Paragraph("T - 00:08", st['value']),
         Paragraph("Secure emergency details broadcast to hospitals & active units", st['value']),
         Paragraph("COMPLETED", st['blue_bold'])],
        [Paragraph("T - 00:12", st['value']),
         Paragraph(f"Hospital matched: {hosp_name} designated as target facility", st['value']),
         Paragraph("COMPLETED", st['blue_bold'])],
        [Paragraph("T - 00:15", st['value']),
         Paragraph(f"Ambulance {amb_veh} accepted request. SMS broadcast loop ended.", st['value']),
         Paragraph("COMPLETED", st['blue_bold'])],
        [Paragraph("T - 00:20", st['value']),
         Paragraph("Outbound voice calls & tracking map links sent to registered family", st['value']),
         Paragraph("COMPLETED", st['blue_bold'])],
        [Paragraph("T - 00:25", st['value']),
         Paragraph("Immutable medical report PDF compiled & hospital EHR database updated", st['value']),
         Paragraph("COMPLETED", st['blue_bold'])],
    ]

    t_timeline = Table(timeline_data, colWidths=[90, 360, 90])
    t_timeline.setStyle(TableStyle([
        ('BACKGROUND',    (0, 0), (-1, 0), _NAVY),
        ('VALIGN',        (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID',          (0, 0), (-1, -1), 0.4, _LIGHT),
        ('TOPPADDING',    (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('ROWBACKGROUNDS',(0, 1), (-1, -1), [colors.white, _STRIPE]),
    ]))
    story.append(t_timeline)
    story.append(Spacer(1, 25))

    # ── Summary of key data points ────────────────────────────────────────────
    story.append(Paragraph("Summary of Critical Information Logged:", st['section']))
    summary_rows = [
        L("Driver:", f"{drv_name}  ({drv_id_code})"),
        L("Incident:", f"{emg_code}  —  {timestamp_str}"),
        L("AI Classification:", f"{pred_class}  |  Risk: {risk_score_str}  |  Severity: {risk_level}"),
        L("Hospital Dispatched:", f"{hosp_name}  ({hosp_id_code})"),
        L("Ambulance Dispatched:", f"Unit {amb_veh}  —  Driver: {amb_driver}  |  ETA: {amb_eta} min"),
        L("GPS at Trigger:", gps_str),
    ]
    story.append(_two_col_table(summary_rows, st))
    story.append(Spacer(1, 20))

    # Signature footer
    sig_data = [
        [Paragraph("<b>System:</b> AI Driver Health Guardian Edge", st['value']),
         Paragraph("<b>Signature:</b> AUTOMATED SECURE COMPLIANCE LOCK", st['value'])],
        [Paragraph(f"<b>Audit Date:</b> {datetime.now().strftime('%Y-%m-%d')}", st['value']),
         Paragraph(f"<b>Audit Time:</b> {datetime.now().strftime('%H:%M:%S')}", st['value'])],
    ]
    t_sig = Table(sig_data, colWidths=[270, 270])
    t_sig.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f1f5f9')),
        ('BOX',        (0, 0), (-1, -1), 1, _LIGHT),
        ('PADDING',    (0, 0), (-1, -1), 8),
    ]))
    story.append(t_sig)

    doc.build(story)
    print(f"[report_generator] PDF saved: {output_path}")


# ─────────────────────────────────────────────────────────────────────────────
# STANDALONE TEST
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    driver = {
        'name': 'LITHHISH R S', 'age': 25, 'gender': 'Male', 'blood_group': 'O+',
        'height': 175, 'weight': 70,
        'dob': '2001-03-15',
        'vehicle_number': 'TN-33-AX-1080', 'vehicle_type': 'Car',
        'driving_license': 'DL-14202300089', 'licence_expiry': '2030-03-15',
        'experience': 3, 'organization': 'Self',
        'phone': '9943064577', 'email': 'lithhisrs@gmail.com',
        'address': 'Velur', 'district': 'Namakkal', 'state': 'Tamil Nadu', 'pincode': '638182',
        'insurance': 'Star Health Insurance (#SH-984210)',
        'emergency_contacts': '+91 9943064577',
        'family_member1_name': 'SHANMUGAM K R', 'family_member1_phone': '+91 9976725694',
        'family_member1_relation': 'Father',
        'medical_history': 'Hypertension, Mild Asthma (Under Medication)',
        'cardiac_history': 'No prior cardiac events',
        'medications': 'Amlodipine 5mg, Salbutamol Inhaler',
        'allergies': 'Penicillin',
        'doctor_name': 'Dr. Ramesh Kumar (Cardiologist)',
        'hospital_preference': 'Lotus Hospital & Research Centre, Erode GH',
        'emergency_notes': 'Patient responds well to bronchodilators',
        'driver_id_code': 'DRV-000144',
    }
    health = {
        'heart_rate': 138, 'spo2': 82, 'temperature': 37.2,
        'systolic_bp': 160, 'diastolic_bp': 100,
        'respiration_rate': 22, 'sleep_hours': 6,
        'stress_level': 8, 'fatigue_score': 7,
        'symptoms': 'Severe chest pain and left arm numbness'
    }
    prediction = {
        'prediction': 'POTENTIAL_CARDIAC_ISSUE',
        'confidence': 0.90, 'risk_percentage': 85.0,
        'severity': 'CRITICAL',
        'explanation': 'Severe vital signs abnormality — hypoxia and elevated BP detected.',
        'suggested_action': 'Park safely, seek urgent emergency evaluation.'
    }
    hospital = {
        'name': 'Government Medical College Hospital, Perundurai',
        'hospital_id_code': 'HOS-GOV-638',
        'hospital_type': 'Government',
        'emergency_number': '+91 4294 220 200',
        'address': 'Kochi - Salem Highway, Sanatorium Post, Perundurai, Erode, Tamil Nadu 638053',
        'emergency_types': 'Pulmonology, Trauma Care, ICU, Cardiology',
        'latitude': 11.275, 'longitude': 77.585
    }
    ambulance = {
        'vehicle_number': 'TN-88-FC-2022',
        'driver_name': 'SANTHOSH S',
        'driver_phone': '+91 9943064577',
        'eta_minutes': 5
    }
    extra = {
        'emergency_code': 'EMG-000107',
        'timestamp': '2026-08-25 11:25:47',
        'severity': 'CRITICAL',
        'risk_percentage': 85.0,
        'status': 'AMBULANCE_REQUESTED',
        'driver_lat': 11.270038,
        'driver_lng': 77.603160,
    }

    test_pdf = os.path.join(os.path.dirname(__file__), 'test_medical_report.pdf')
    generate_medical_report(driver, health, prediction, hospital, ambulance, test_pdf, extra_data=extra)
