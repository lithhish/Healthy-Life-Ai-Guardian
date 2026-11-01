import random
import string
from datetime import datetime, timedelta
from extensions import db
from models import OTPVerification

class OTPService:
    @staticmethod
    def generate_otp(phone: str, purpose: str = 'login') -> str:
        otp_code = ''.join(random.choices(string.digits, k=6))
        expires_at = datetime.utcnow() + timedelta(minutes=10)
        
        verification = OTPVerification(
            phone=phone,
            otp=otp_code,
            purpose=purpose,
            expires_at=expires_at
        )
        db.session.add(verification)
        db.session.commit()
        
        # Simulated sending - in a real app, integrate Twilio here
        print(f"\n[DEMO OTP MODE] OTP SENT TO: {phone}")
        print(f"[DEMO OTP MODE] YOUR CODE IS: {otp_code}\n")
        
        return otp_code
        
    @staticmethod
    def verify_otp(phone: str, otp: str, purpose: str = 'login') -> bool:
        verification = OTPVerification.query.filter_by(
            phone=phone, 
            otp=otp, 
            purpose=purpose, 
            verified=False
        ).order_by(OTPVerification.created_at.desc()).first()
        
        if not verification:
            return False
            
        if verification.expires_at < datetime.utcnow():
            return False
            
        verification.verified = True
        db.session.commit()
        return True
