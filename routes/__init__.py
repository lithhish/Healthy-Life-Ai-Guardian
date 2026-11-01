from flask import request, redirect
from config import Config
from .auth import auth_bp
from .main import main_bp
from .api import api_bp
from .admin import admin_bp
from .hospital import hospital_bp
from .twilio_routes import twilio_bp

def register_routes(app):
    @app.template_filter('local_time')
    def format_local_time(dt_val):
        if not dt_val:
            return ""
        from datetime import datetime, timedelta
        dt_str = str(dt_val)
        try:
            clean_str = dt_str.replace('Z', '').split('.')[0]
            if 'T' in clean_str:
                dt_obj = datetime.fromisoformat(clean_str)
            else:
                dt_obj = datetime.strptime(clean_str, '%Y-%m-%d %H:%M:%S')
            
            now_utc = datetime.utcnow()
            now_local = datetime.now()
            diff_hours = (now_local - now_utc).total_seconds() / 3600.0
            if diff_hours > 1.0:
                age_local_sec = (now_local - dt_obj).total_seconds()
                if age_local_sec > 18000:
                    dt_obj = dt_obj + timedelta(hours=5, minutes=30)
            return dt_obj.strftime('%Y-%m-%d %H:%M:%S')
        except Exception:
            return dt_str

    @app.before_request
    def force_https():
        import sys
        if getattr(Config, 'HTTPS_ENABLED', False) and not request.is_secure and not app.testing and not app.config.get('TESTING') and 'unittest' not in sys.modules:
            if request.headers.get('X-Forwarded-Proto', 'http') == 'http':
                url = request.url.replace("http://", "https://", 1)
                return redirect(url, code=301)

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(api_bp, url_prefix='/api')
    app.register_blueprint(admin_bp)
    app.register_blueprint(hospital_bp)
    app.register_blueprint(twilio_bp)

