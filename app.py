from flask import Flask
from config import Config
from extensions import db, socketio
from routes import register_routes
from models import *

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Initialize extensions
    db.init_app(app)
    socketio.init_app(app, cors_allowed_origins="*")

    # Pre-warm AI models for instantaneous vital analysis
    try:
        from ai_engine import initialize_models
        initialize_models()
    except Exception as e:
        print(f"[AI MODEL INIT WARNING] {e}")

    # Register Blueprints
    register_routes(app)

    return app

app = create_app()

if __name__ == '__main__':
    base_url = getattr(Config, 'BASE_URL', '')
    if 'localhost' in base_url or '127.0.0.1' in base_url:
        print("\n=========================================================================================")
        print("[WARNING] Config.BASE_URL is set to localhost/127.0.0.1.")
        print("Twilio calls will NOT be able to reach your local server webhooks!")
        print("Please set BASE_URL to a public HTTPS URL (e.g., ngrok tunnel URL) in your .env file.")
        print("=========================================================================================\n")
    import os
    ssl_args = {}
    if getattr(Config, 'HTTPS_ENABLED', False):
        cert_file = getattr(Config, 'APP_SSL_CERT_FILE', 'certs/server.crt')
        key_file = getattr(Config, 'APP_SSL_KEY_FILE', 'certs/server.key')
        if os.path.exists(cert_file) and os.path.exists(key_file):
            # Validate matching keypair to prevent KEY_VALUES_MISMATCH
            try:
                from cryptography import x509
                from cryptography.hazmat.primitives import serialization
                with open(cert_file, 'rb') as f:
                    cert_data = x509.load_pem_x509_certificate(f.read())
                with open(key_file, 'rb') as f:
                    key_data = serialization.load_pem_private_key(f.read(), password=None)
                if cert_data.public_key().public_numbers() != key_data.public_key().public_numbers():
                    raise ValueError("SSL Certificate public key does not match private key!")
            except Exception as e:
                print(f"[SSL VALIDATION ERROR] Certificate key mismatch: {e}")
                raise

            ssl_args['ssl_context'] = (cert_file, key_file)
            print(f"[HTTPS] Serving server securely on HTTPS with matching cert: {cert_file}")
        else:
            print("[HTTPS WARNING] SSL Certificate files not found, starting over HTTP.")
            
    socketio.run(app, debug=False, host='0.0.0.0', port=5000, allow_unsafe_werkzeug=True, **ssl_args)
