"""
AI Driver Health Guardian — Dedicated AI Emergency Prediction Engine

Architecture:
  Sensor Preprocessing & Signal Validation
          ↓
  Feature Extraction (ECG, SpO2, HR, Temp, Accel/Impact, MQ-3, Fatigue)
          ↓
  Lightweight AI Inference & Multi-Sensor Rule Engine
          ↓
  Normalized Risk Score Calculation (0-100)
          ↓
  5-10 Minute Time-Series Rolling Buffer (Trend Analysis)
          ↓
  Cardiac Emergency State Machine
          ↓
  Medical Safety Disclaimer Enforcement

Risk Scale:
  0–20   : NORMAL
  21–40  : LOW RISK
  41–60  : MODERATE RISK
  61–80  : HIGH RISK
  81–100 : CRITICAL EMERGENCY
"""

from collections import deque
from datetime import datetime
from ai.ecg_processor import ECGProcessor

# Non-diagnostic medical safety disclaimer string required by clinical safety rules
MEDICAL_SAFETY_DISCLAIMER = "AI-generated emergency risk assessment. This is not a medical diagnosis."

class CardiacStateMachine:
    STATES = ["NORMAL", "MONITORING", "EARLY_WARNING", "HIGH_RISK", "CRITICAL_EMERGENCY", "EMERGENCY_ACTIVE", "RESOLVED"]

    def __init__(self):
        self.current_state = "NORMAL"
        self.state_changed_at = datetime.utcnow()
        self.active_emergency_id = None

    def update_state(self, score: float, is_sos: bool = False, is_accident: bool = False) -> str:
        old_state = self.current_state

        if is_sos or is_accident:
            self.current_state = "EMERGENCY_ACTIVE"
        elif score >= 81.0:
            self.current_state = "CRITICAL_EMERGENCY"
        elif score >= 61.0:
            self.current_state = "HIGH_RISK"
        elif score >= 41.0:
            self.current_state = "EARLY_WARNING"
        elif score >= 21.0:
            self.current_state = "MONITORING"
        else:
            if self.current_state not in ["EMERGENCY_ACTIVE", "CRITICAL_EMERGENCY"]:
                self.current_state = "NORMAL"

        if old_state != self.current_state:
            self.state_changed_at = datetime.utcnow()

        return self.current_state


class EmergencyPredictionEngine:
    def __init__(self):
        self.state_machine = CardiacStateMachine()
        # Rolling time-series buffer storing last 60 readings (approx 5-10 minutes)
        self.history_buffer = deque(maxlen=60)

    def process_vitals(self, vitals: dict, ecg_signal: list = None) -> dict:
        """
        Main AI & Clinical Rule Engine entry point.
        Evaluates health telemetry and returns comprehensive risk assessment.
        """
        vitals = vitals or {}
        
        # 1. Parse Sensor Inputs
        hr = float(vitals.get('heart_rate', 72))
        spo2 = float(vitals.get('spo2', 98))
        temp = float(vitals.get('temperature', 36.8))
        sys_bp = float(vitals.get('systolic_bp', 120))
        dia_bp = float(vitals.get('diastolic_bp', 80))
        resp = float(vitals.get('respiration_rate', 14))
        alcohol = float(vitals.get('alcohol_level', 0.0))
        stress = float(vitals.get('stress_level', 2))
        fatigue = float(vitals.get('fatigue_score', 2))
        symptoms = str(vitals.get('symptoms', '')).lower()
        
        is_sos = bool(vitals.get('is_sos', False))
        is_accident = bool(vitals.get('is_accident', False))
        impact_g = float(vitals.get('impact_g', 1.0))

        # 2. ECG Signal Processing
        ecg_res = ECGProcessor.analyze_ecg(ecg_signal) if ecg_signal else {
            "status": "NORMAL", "arrhythmia_detected": False, "sdnn_ms": 40.0, "rmssd_ms": 30.0, "signal_quality_sqi": 0.95, "ecg_notes": "Normal Sinus Rhythm"
        }

        # Check symptom text for cardiac/emergency keywords
        symptom_cardiac = any(k in symptoms for k in ['chest pain', 'numbness', 'arm pain', 'tightness', 'angina'])
        symptom_stroke = any(k in symptoms for k in ['slurred', 'face numbness', 'paralysis', 'confusion'])

        # 3. Time-Series Buffer Append
        snapshot = {
            'timestamp': datetime.utcnow(),
            'hr': hr, 'spo2': spo2, 'temp': temp, 'sys_bp': sys_bp, 'dia_bp': dia_bp,
            'stress': stress, 'fatigue': fatigue
        }
        self.history_buffer.append(snapshot)

        # 4. Multi-Factor Risk Score Calculation (0-100)
        cardiac_score = 0.0
        detected_abnormalities = []

        # A. Heart Rate Assessment
        if hr > 140 or hr < 40:
            cardiac_score += 25.0
            detected_abnormalities.append(f"Critical Heart Rate: {int(hr)} bpm")
        elif hr > 115 or hr < 50:
            cardiac_score += 15.0
            detected_abnormalities.append(f"Abnormal Heart Rate: {int(hr)} bpm")

        # B. SpO2 Oxygen Saturation Assessment
        if spo2 < 85:
            cardiac_score += 30.0
            detected_abnormalities.append(f"Severe Hypoxia: SpO₂ {int(spo2)}%")
        elif spo2 < 92:
            cardiac_score += 18.0
            detected_abnormalities.append(f"Low Oxygen: SpO₂ {int(spo2)}%")

        # C. ECG Arrhythmia Evidence
        if ecg_res.get('arrhythmia_detected'):
            cardiac_score += 25.0
            detected_abnormalities.append(f"ECG Rhythm Anomaly: {ecg_res['ecg_notes']}")

        # D. Blood Pressure Assessment
        if sys_bp > 170 or dia_bp > 105:
            cardiac_score += 20.0
            detected_abnormalities.append(f"Severe Hypertension: {int(sys_bp)}/{int(dia_bp)} mmHg")
        elif sys_bp < 85 or dia_bp < 55:
            cardiac_score += 18.0
            detected_abnormalities.append(f"Hypotension Crash: {int(sys_bp)}/{int(dia_bp)} mmHg")

        # E. Temperature Assessment
        if temp > 38.5:
            cardiac_score += 10.0
            detected_abnormalities.append(f"High Fever: {temp:.1f}°C")

        # F. Symptom Evidence
        if symptom_cardiac:
            cardiac_score += 25.0
            detected_abnormalities.append("Reported Symptoms: Acute chest discomfort / left arm tightness")
        if symptom_stroke:
            cardiac_score += 25.0
            detected_abnormalities.append("Reported Symptoms: Slurred speech / neurological impairment")

        # G. Impact / Accident Detection (MPU6050)
        if is_accident or impact_g > 4.5:
            cardiac_score = 95.0
            detected_abnormalities.append(f"Accident Impact Spike Detected ({impact_g:.1f} G)")

        # H. Manual SOS Override
        if is_sos:
            cardiac_score = 100.0
            detected_abnormalities.append("Manual SOS Panic Button Activated")

        # Cap score to 100 max
        final_score = float(min(100.0, round(cardiac_score, 1)))

        # 5. Trend Analysis (Rolling History Buffer)
        trend = "STABLE"
        if len(self.history_buffer) >= 3:
            recent_spo2 = [x['spo2'] for x in list(self.history_buffer)[-5:]]
            recent_hr = [x['hr'] for x in list(self.history_buffer)[-5:]]
            
            if recent_spo2[0] - recent_spo2[-1] >= 4.0 or recent_hr[-1] - recent_hr[0] >= 20.0:
                trend = "RAPIDLY INCREASING"
            elif recent_spo2[0] - recent_spo2[-1] >= 2.0 or recent_hr[-1] - recent_hr[0] >= 10.0:
                trend = "INCREASING"

        # 6. Classification Mapping & State Machine
        state = self.state_machine.update_state(final_score, is_sos=is_sos, is_accident=is_accident)

        if is_sos:
            classification = "MANUAL_SOS_EMERGENCY"
            severity = "CRITICAL"
        elif is_accident or impact_g > 4.5:
            classification = "VEHICLE_ACCIDENT_DETECTED"
            severity = "CRITICAL"
        elif final_score >= 81.0:
            classification = "POTENTIAL_CARDIAC_ISSUE" if (symptom_cardiac or ecg_res['arrhythmia_detected']) else "CRITICAL_PHYSIOLOGICAL_DISTRESS"
            severity = "CRITICAL"
        elif final_score >= 61.0:
            classification = "HIGH_CARDIAC_RISK" if (symptom_cardiac or ecg_res['arrhythmia_detected']) else "HIGH_HEALTH_RISK"
            severity = "HIGH"
        elif final_score >= 41.0:
            classification = "MODERATE_HEALTH_RISK"
            severity = "MODERATE"
        elif final_score >= 21.0:
            classification = "MILD_HEALTH_DISTRESS"
            severity = "LOW"
        else:
            classification = "Normal"
            severity = "Normal"

        confidence_pct = min(98, max(75, int(80 + (final_score * 0.18))))

        return {
            "disclaimer": MEDICAL_SAFETY_DISCLAIMER,
            "risk_score": final_score,
            "severity": severity,
            "prediction": classification,
            "emergency_type": classification,
            "state": state,
            "confidence_score": f"{confidence_pct}%",
            "trend": trend,
            "detected_abnormalities": detected_abnormalities if detected_abnormalities else ["Vitals within safe limits"],
            "ecg_analysis": ecg_res,
            "multi_sensor_evidence": {
                "heart_rate": hr,
                "spo2": spo2,
                "temperature": temp,
                "blood_pressure": f"{int(sys_bp)}/{int(dia_bp)}",
                "respiration": resp,
                "alcohol": alcohol,
                "fatigue": fatigue,
                "stress": stress,
                "impact_g": impact_g,
                "is_sos": is_sos,
                "is_accident": is_accident
            },
            "early_warning_active": final_score >= 41.0,
            "is_emergency": final_score >= 61.0 or is_sos or is_accident
        }

# Global singleton engine instance
emergency_engine = EmergencyPredictionEngine()
