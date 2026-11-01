import os
import socket
from dotenv import load_dotenv
load_dotenv()

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = os.environ.get('FLASK_SECRET_KEY', 'default-secret-key-for-dev')
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or f"sqlite:///{os.path.join(BASE_DIR, 'guardian.db')}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    GOOGLE_MAPS_API_KEY = os.environ.get('GOOGLE_MAPS_API_KEY', '')
    GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', '')
    
    TWILIO_ACCOUNT_SID = os.environ.get('TWILIO_ACCOUNT_SID', '')
    TWILIO_AUTH_TOKEN = os.environ.get('TWILIO_AUTH_TOKEN', '')
    TWILIO_PHONE_NUMBER = os.environ.get('TWILIO_PHONE_NUMBER', '')
    TWILIO_TEST_MODE = os.environ.get('TWILIO_TEST_MODE', 'true').lower() == 'true'
    MAX_AMBULANCE_CALL_ATTEMPTS = int(os.environ.get('MAX_AMBULANCE_CALL_ATTEMPTS', 3))
    CALL_RING_TIMEOUT = int(os.environ.get('CALL_RING_TIMEOUT', 30))
    GATHER_TIMEOUT = int(os.environ.get('GATHER_TIMEOUT', 15))
    MAX_GATHER_RETRIES = int(os.environ.get('MAX_GATHER_RETRIES', 2))
    EMERGENCY_COOLDOWN_SECONDS = int(os.environ.get('EMERGENCY_COOLDOWN_SECONDS', 300))
    def _get_local_ip():
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(('8.8.8.8', 1))
            IP = s.getsockname()[0]
        except Exception:
            IP = '127.0.0.1'
        finally:
            s.close()
        return IP

    _detected_ip = _get_local_ip()
    BASE_URL = os.environ.get('BASE_URL', f'https://{_detected_ip}:5000')
    if '10.237.68.36' in BASE_URL:
        BASE_URL = BASE_URL.replace('10.237.68.36', _detected_ip)
    elif 'localhost' in BASE_URL:
        BASE_URL = BASE_URL.replace('localhost', _detected_ip)
    elif '127.0.0.1' in BASE_URL:
        BASE_URL = BASE_URL.replace('127.0.0.1', _detected_ip)
    
    HTTPS_ENABLED = os.environ.get('HTTPS_ENABLED', 'false').lower() == 'true'
    APP_SSL_CERT_FILE = os.environ.get('APP_SSL_CERT_FILE', 'certs/server.crt')
    APP_SSL_KEY_FILE = os.environ.get('APP_SSL_KEY_FILE', 'certs/server.key')
    
    SESSION_COOKIE_SECURE = HTTPS_ENABLED
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'

