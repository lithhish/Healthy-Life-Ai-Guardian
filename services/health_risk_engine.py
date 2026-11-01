class HealthRiskEngine:
    @staticmethod
    def evaluate_risk(vitals):
        """
        vitals: dict containing heart_rate, spo2, blood_pressure_sys, blood_pressure_dia, alcohol
        """
        risk_level = "LOW"
        emergency_type = "NORMAL"
        alerts = []

        # Alcohol Check
        alcohol = vitals.get('alcohol', 0)
        if alcohol > 0.08:
            risk_level = "CRITICAL"
            emergency_type = "ALCOHOL_IMPAIRMENT"
            alerts.append("Alcohol detected. Do not drive.")

        # Heart Rate Check
        hr = vitals.get('heart_rate', 75)
        if hr > 140 or hr < 40:
            risk_level = "CRITICAL"
            emergency_type = "CARDIAC_EMERGENCY"
            alerts.append("Critical Heart Rate detected.")
        elif hr > 100 or hr < 50:
            risk_level = max(risk_level, "HIGH")
            if emergency_type == "NORMAL": emergency_type = "POTENTIAL_CARDIAC_ISSUE"
            alerts.append("Abnormal Heart Rate.")

        # SpO2 Check
        spo2 = vitals.get('spo2', 98)
        if spo2 < 90:
            risk_level = "CRITICAL"
            emergency_type = "SEVERE_HYPOXIA"
            alerts.append("Critical Oxygen Saturation.")
        elif spo2 < 94:
            risk_level = max(risk_level, "HIGH")
            if emergency_type == "NORMAL": emergency_type = "LOW_OXYGEN"
            alerts.append("Low Oxygen Saturation.")

        # BP Check
        sys = vitals.get('blood_pressure_sys', 120)
        dia = vitals.get('blood_pressure_dia', 80)
        if sys > 180 or dia > 120:
            risk_level = "CRITICAL"
            emergency_type = "HYPERTENSIVE_CRISIS"
            alerts.append("Hypertensive Crisis detected.")
        elif sys > 140 or dia > 90:
            risk_level = max(risk_level, "MEDIUM")
            if emergency_type == "NORMAL": emergency_type = "ELEVATED_BP"
            alerts.append("Elevated Blood Pressure.")

        return {
            "risk_level": risk_level,
            "emergency_type": emergency_type,
            "alerts": alerts
        }
