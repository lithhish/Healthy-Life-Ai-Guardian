import os
import re
from twilio.rest import Client
from config import Config

class TwilioService:
    _client = None

    @classmethod
    def get_twilio_client(cls):
        """Returns a singleton Twilio Client instance if credentials are valid."""
        if cls._client is not None:
            return cls._client

        sid = Config.TWILIO_ACCOUNT_SID
        token = Config.TWILIO_AUTH_TOKEN

        if not sid or not token:
            print("[TwilioService] Warning: Twilio credentials not configured.")
            return None

        try:
            cls._client = Client(sid, token)
            return cls._client
        except Exception as e:
            print(f"[TwilioService] Error initializing client: {e}")
            return None

    @staticmethod
    def normalize_phone_number(phone: str, default_country_code: str = "+91") -> str:
        """
        Normalizes phone numbers to E.164 format.
        E.g. 9876543210 -> +919876543210.
        If number already has '+' or matches E.164, keeps it.
        """
        if not phone:
            return ""
        # Remove non-numeric characters except +
        cleaned = re.sub(r"[^\d+]", "", phone.strip())
        
        if cleaned.startswith("+"):
            return cleaned
        
        if cleaned.startswith("00"):
            return "+" + cleaned[2:]
            
        # If it's a 10-digit number and has no country code, prepend default
        if len(cleaned) == 10:
            return default_country_code + cleaned
            
        # If it starts with country code without '+' (like 919876543210)
        if len(cleaned) == 12 and cleaned.startswith("91"):
            return "+" + cleaned
        if len(cleaned) == 11 and cleaned.startswith("1"):
            return "+" + cleaned
            
        # Return as is if we can't determine, or prepend + if numeric
        if cleaned.isdigit():
            return "+" + cleaned
        return cleaned

    @classmethod
    def send_sms(cls, to: str, body: str) -> dict:
        """Sends an SMS using Twilio Client."""
        # Real Mode Safety Validation
        is_test_mode = getattr(Config, 'TWILIO_TEST_MODE', True)
        sid = Config.TWILIO_ACCOUNT_SID
        token = Config.TWILIO_AUTH_TOKEN
        from_num = Config.TWILIO_PHONE_NUMBER

        if not is_test_mode:
            if not sid or not token or not from_num or from_num != '+18166645704':
                return {"success": False, "error": "TWILIO_CONFIGURATION_ERROR", "status": "FAILED"}

        if is_test_mode:
            # Simulated test mode response
            return {"success": True, "sid": "SMmocked1234567890abcdef123456789", "status": "SENT"}

        client = cls.get_twilio_client()
        if not client or not from_num:
            return {"success": False, "error": "TWILIO_CONFIGURATION_ERROR", "status": "FAILED"}

        to_normalized = cls.normalize_phone_number(to)
        
        try:
            callback_url = f"{Config.BASE_URL.rstrip('/')}/api/twilio/sms/status" if getattr(Config, 'BASE_URL', '') else None
            message = client.messages.create(
                to=to_normalized,
                from_=from_num,
                body=body,
                status_callback=callback_url
            )
            return {
                "success": True,
                "sid": message.sid,
                "status": message.status.upper()
            }
        except Exception as e:
            err_msg = str(e)
            print(f"[TwilioService] Send SMS failed: {err_msg}")
            # Detect A2P 10DLC rejection
            if "A2P" in err_msg or "30007" in err_msg or "30008" in err_msg:
                status = "FAILED"
                error_detail = f"A2P 10DLC Compliance Rejection: {err_msg}"
            else:
                status = "FAILED"
                error_detail = err_msg
            return {"success": False, "error": error_detail, "status": status}

    @classmethod
    def initiate_voice_call(cls, to: str, twiml_url: str, status_callback_url: str = None) -> dict:
        """Initiates an outbound voice call pointing to a TwiML URL."""
        # Real Mode Safety Validation
        is_test_mode = getattr(Config, 'TWILIO_TEST_MODE', True)
        sid = Config.TWILIO_ACCOUNT_SID
        token = Config.TWILIO_AUTH_TOKEN
        from_num = Config.TWILIO_PHONE_NUMBER

        if not is_test_mode:
            if not sid or not token or not from_num or from_num != '+18166645704':
                return {"success": False, "error": "TWILIO_CONFIGURATION_ERROR", "status": "FAILED"}

        if is_test_mode:
            # Simulated test mode response
            return {"success": True, "sid": "CAmocked1234567890abcdef123456789", "status": "QUEUED"}

        client = cls.get_twilio_client()
        if not client or not from_num:
            return {"success": False, "error": "TWILIO_CONFIGURATION_ERROR", "status": "FAILED"}

        to_normalized = cls.normalize_phone_number(to)

        try:
            kwargs = {
                "to": to_normalized,
                "from_": from_num,
                "url": twiml_url,
                "timeout": Config.CALL_RING_TIMEOUT
            }
            if status_callback_url:
                kwargs["status_callback"] = status_callback_url
                kwargs["status_callback_event"] = ["initiated", "ringing", "answered", "completed"]
                kwargs["status_callback_method"] = "POST"
                
            call = client.calls.create(**kwargs)
            return {
                "success": True,
                "sid": call.sid,
                "status": call.status.upper()
            }
        except Exception as e:
            print(f"[TwilioService] Initiate voice call failed: {e}")
            return {"success": False, "error": str(e), "status": "FAILED"}
