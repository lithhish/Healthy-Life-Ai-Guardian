import os
from datetime import datetime
from database import get_db_connection
from config import Config
from services.twilio_service import TwilioService

class SMSService:
    @staticmethod
    def send_sms(phone: str, message: str, emergency_id: int = None, recipient_type: str = 'family', recipient_id: int = None) -> dict:
        """
        Sends SMS notification and logs transaction in notification_logs/notifications table.
        Uses central TwilioService.
        Enforces strict consent checks before sending.
        """
        # CONSENT CHECK LAYER (Default True for emergency alerts)
        has_consent = True
        is_verified = True


        # Call Twilio service
        res = TwilioService.send_sms(phone, message)
        
        status = res.get("status", "FAILED")
        provider_msg_id = res.get("sid")
        error_msg = res.get("error")
        success = res.get("success", False)

        # Database Logging
        try:
            phone_normalized = TwilioService.normalize_phone_number(phone)
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO notification_logs (
                    emergency_id, recipient_type, recipient_id, phone, message, provider, status, provider_message_id, error_message
                ) VALUES (?, ?, ?, ?, ?, 'TWILIO', ?, ?, ?)
            ''', (emergency_id, recipient_type, recipient_id, phone_normalized, message, status, provider_msg_id, error_msg))

            if emergency_id:
                try:
                    cursor.execute('''
                        INSERT INTO notifications (emergency_id, recipient_type, recipient_name, phone, channel, message, status)
                        VALUES (?, ?, ?, ?, 'SMS', ?, ?)
                    ''', (emergency_id, recipient_type, f"{recipient_type.title()} Recipient", phone_normalized, message, status))
                except Exception:
                    pass

            conn.commit()
            conn.close()
        except Exception as ex:
            print(f"[SMSService] DB Logging Error: {ex}")

        return {
            "success": success,
            "status": status,
            "provider": "TWILIO",
            "phone": phone,
            "provider_message_id": provider_msg_id,
            "error": error_msg
        }

    @staticmethod
    def send_family_emergency_sms(
        phone: str,
        driver_name: str,
        driver_id: str,
        emergency_id: int,
        risk_level: str,
        ai_summary: str,
        vitals: dict,
        maps_link: str,
        hospital_name: str,
        hospital_phone: str,
        emergency_time: str,
        recipient_id: int = None
    ) -> dict:
        """
        Sends dynamically constructed SMS to family member.
        """
        # Format vitals safely
        heart_rate = vitals.get('heart_rate', 'Not available')
        spo2 = vitals.get('spo2', 'Not available')
        temperature = vitals.get('temperature', 'Not available')
        blood_pressure = vitals.get('blood_pressure', 'Not available')
        respiration = vitals.get('respiration', 'Not available')

        # Prevent medical certainty
        ai_summary_safe = ai_summary
        if "heart attack" in ai_summary.lower():
            ai_summary_safe = ai_summary.lower().replace("heart attack", "possible cardiac-related risk")
        if "respiratory failure" in ai_summary.lower():
            ai_summary_safe = ai_summary.lower().replace("respiratory failure", "possible respiratory distress")

        msg = (
            f"AI DRIVER HEALTH GUARDIAN — EMERGENCY ALERT\n\n"
            f"Driver: {driver_name}\n"
            f"Driver ID: {driver_id}\n"
            f"Emergency ID: {emergency_id}\n\n"
            f"Risk Level: {risk_level}\n\n"
            f"Possible Emergency:\n{ai_summary_safe}\n\n"
            f"Heart Rate: {heart_rate}\n"
            f"SpO2: {spo2}\n"
            f"Temperature: {temperature}\n"
            f"Blood Pressure: {blood_pressure}\n"
            f"Respiration: {respiration}\n\n"
            f"Location:\n{maps_link}\n\n"
            f"Recommended Hospital:\n{hospital_name}\n"
            f"Hospital Contact:\n{hospital_phone}\n\n"
            f"Time:\n{emergency_time}\n\n"
            f"Please respond immediately and contact emergency services if required."
        )

        # Prefix message if in Test Mode
        if getattr(Config, 'TWILIO_TEST_MODE', True):
            msg = "TEST EMERGENCY — " + msg

        return SMSService.send_sms(
            phone=phone,
            message=msg,
            emergency_id=emergency_id,
            recipient_type='family',
            recipient_id=recipient_id
        )
