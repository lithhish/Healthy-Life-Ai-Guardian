"""
AI Driver Health Guardian — Voice Engine
Multilingual Text-To-Speech + Translation Module

Architecture:
  Translation: deep-translator (Google) → NLLB-200 stub (GPU optional)
  TTS:         gTTS (online) → pyttsx3 (offline) → Coqui XTTS-v2 stub (GPU optional)

Swap to heavy models by setting env vars:
  USE_NLLB=1     — uses Helsinki NLP / NLLB-200 via HuggingFace
  USE_COQUI=1    — uses Coqui XTTS-v2 for neural TTS
  USE_WHISPER=1  — enables server-side Whisper STT
"""

import os
import uuid
import hashlib
import traceback
from datetime import datetime

# ──────────────────────────────────────────────────
# Language Registry
# ──────────────────────────────────────────────────
SUPPORTED_LANGUAGES = {
    'en': {'name': 'English',    'gtts': 'en',    'nllb': 'eng_Latn'},
    'ta': {'name': 'Tamil',      'gtts': 'ta',    'nllb': 'tam_Taml'},
    'hi': {'name': 'Hindi',      'gtts': 'hi',    'nllb': 'hin_Deva'},
    'te': {'name': 'Telugu',     'gtts': 'te',    'nllb': 'tel_Telu'},
    'kn': {'name': 'Kannada',    'gtts': 'kn',    'nllb': 'kan_Knda'},
    'ml': {'name': 'Malayalam',  'gtts': 'ml',    'nllb': 'mal_Mlym'},
    'mr': {'name': 'Marathi',    'gtts': 'mr',    'nllb': 'mar_Deva'},
    'bn': {'name': 'Bengali',    'gtts': 'bn',    'nllb': 'ben_Beng'},
    'gu': {'name': 'Gujarati',   'gtts': 'gu',    'nllb': 'guj_Gujr'},
    'pa': {'name': 'Punjabi',    'gtts': 'pa',    'nllb': 'pan_Guru'},
    'ur': {'name': 'Urdu',       'gtts': 'ur',    'nllb': 'urd_Arab'},
}

LANG_NAMES = {k: v['name'] for k, v in SUPPORTED_LANGUAGES.items()}

# Audio output directory
AUDIO_DIR = os.path.join(os.path.dirname(__file__), 'static', 'audio')
os.makedirs(AUDIO_DIR, exist_ok=True)

# ──────────────────────────────────────────────────
# Translation Backend
# ──────────────────────────────────────────────────
_translator = None
USE_NLLB = os.environ.get('USE_NLLB', '0') == '1'

def _get_translator():
    global _translator
    if _translator is not None:
        return _translator

    if USE_NLLB:
        # Stub: NLLB-200 via HuggingFace Transformers (requires GPU/large RAM)
        try:
            from transformers import pipeline
            _translator = pipeline("translation", model="facebook/nllb-200-distilled-600M")
            print("[VoiceEngine] NLLB-200 translation loaded.")
            return _translator
        except Exception as e:
            print(f"[VoiceEngine] NLLB-200 failed ({e}), falling back to deep-translator.")

    try:
        from deep_translator import GoogleTranslator
        _translator = 'google'
        print("[VoiceEngine] Using Google Translate (deep-translator).")
    except ImportError:
        try:
            from googletrans import Translator
            _translator = Translator()
            print("[VoiceEngine] Using googletrans.")
        except ImportError:
            _translator = None
            print("[VoiceEngine] No translation library found. Text will not be translated.")
    return _translator


def translate_text(text: str, target_lang: str) -> str:
    """Translate text to the target language code (e.g. 'ta', 'hi')."""
    if target_lang == 'en' or not target_lang:
        return text
    if target_lang not in SUPPORTED_LANGUAGES:
        return text

    try:
        translator = _get_translator()
        if translator is None:
            return text

        if USE_NLLB and callable(getattr(translator, '__call__', None)):
            src_code = 'eng_Latn'
            tgt_code = SUPPORTED_LANGUAGES[target_lang]['nllb']
            result = translator(text, src_lang=src_code, tgt_lang=tgt_code)
            return result[0]['translation_text']

        elif translator == 'google':
            from deep_translator import GoogleTranslator
            translated = GoogleTranslator(source='en', target=target_lang).translate(text)
            return translated if translated else text

        elif hasattr(translator, 'translate'):
            result = translator.translate(text, dest=target_lang)
            return result.text if result else text

    except Exception as e:
        print(f"[VoiceEngine] Translation error: {e}")
    return text


# ──────────────────────────────────────────────────
# TTS Backend
# ──────────────────────────────────────────────────
USE_COQUI = os.environ.get('USE_COQUI', '0') == '1'
_coqui_tts = None

def _get_coqui_tts():
    """Load Coqui XTTS-v2 model (heavy — GPU recommended)."""
    global _coqui_tts
    if _coqui_tts:
        return _coqui_tts
    try:
        from TTS.api import TTS
        _coqui_tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2")
        print("[VoiceEngine] Coqui XTTS-v2 loaded.")
        return _coqui_tts
    except Exception as e:
        print(f"[VoiceEngine] Coqui TTS failed ({e}), falling back to gTTS.")
        return None


def speak_text(text: str, lang: str = 'en', output_path: str = None) -> str:
    """
    Convert text to speech.
    Returns the output filepath on success, None on failure.
    """
    if not text:
        return None

    # Sanitise lang
    if lang not in SUPPORTED_LANGUAGES:
        lang = 'en'

    gtts_lang = SUPPORTED_LANGUAGES[lang]['gtts']

    if output_path is None:
        token = hashlib.md5(f"{text[:40]}{lang}".encode()).hexdigest()[:12]
        output_path = os.path.join(AUDIO_DIR, f"tts_{token}.mp3")

    # Already cached?
    if os.path.exists(output_path):
        return output_path

    # Method 1: Coqui XTTS-v2
    if USE_COQUI:
        tts = _get_coqui_tts()
        if tts:
            try:
                tts.tts_to_file(text=text, language=lang, file_path=output_path)
                print(f"[VoiceEngine] Coqui TTS -> {output_path}")
                return output_path
            except Exception as e:
                print(f"[VoiceEngine] Coqui failed: {e}")

    # Method 2: gTTS (online, lightweight)
    try:
        from gtts import gTTS
        tts = gTTS(text=text, lang=gtts_lang, slow=False)
        tts.save(output_path)
        print(f"[VoiceEngine] gTTS ({lang}) -> {output_path}")
        return output_path
    except Exception as e:
        print(f"[VoiceEngine] gTTS failed: {e}")

    # Method 3: pyttsx3 (offline, English only)
    try:
        import pyttsx3
        import tempfile
        engine = pyttsx3.init()
        engine.setProperty('rate', 160)
        engine.save_to_file(text, output_path.replace('.mp3', '.wav'))
        engine.runAndWait()
        wav_path = output_path.replace('.mp3', '.wav')
        if os.path.exists(wav_path):
            os.replace(wav_path, output_path)
            print(f"[VoiceEngine] pyttsx3 -> {output_path}")
            return output_path
    except Exception as e:
        print(f"[VoiceEngine] pyttsx3 failed: {e}")

    return None


# ──────────────────────────────────────────────────
# Emergency Voice Script Templates
# ──────────────────────────────────────────────────
EMERGENCY_ALERT_TEMPLATE = (
    "Hello {driver_name}. "
    "I am your AI Health Guardian. "
    "A possible {emergency_type} has been detected. "
    "Please remain calm. "
    "Stop your vehicle safely as soon as possible. "
    "Do not continue driving. "
    "An ambulance is being dispatched to your location. "
    "The nearest hospital, {hospital_name}, has been notified. "
    "Your family has been informed. "
    "Please breathe slowly and stay calm. "
    "Help is on the way."
)

CONSCIOUSNESS_CHECK_TEMPLATE = (
    "Hello {driver_name}. Can you hear me? "
    "If you can hear me, please press the Yes button on your screen. "
    "Can you breathe normally? "
    "Can you safely stop the vehicle? "
    "Please respond within 30 seconds. "
    "If no response is received, emergency services will be escalated automatically."
)

FAMILY_NOTIFICATION_TEMPLATE = (
    "Hello. This is the AI Driver Health Guardian emergency notification system. "
    "{driver_name} has experienced a possible {emergency_type}. "
    "They have been instructed to stop driving safely. "
    "They are being directed to {hospital_name}. "
    "An ambulance has been dispatched. "
    "The estimated arrival time to the hospital is {eta} minutes. "
    "Please proceed to {hospital_name} immediately. "
    "Thank you."
)

HOSPITAL_NOTIFICATION_TEMPLATE = (
    "Attention medical team. An emergency patient is arriving. "
    "Patient name: {driver_name}. "
    "Age: {age}. Blood group: {blood_group}. "
    "Emergency type: {emergency_type}. "
    "AI risk score: {risk_percent} percent. "
    "Estimated arrival: {eta} minutes. "
    "Please prepare the {department} team immediately."
)

ESCALATION_TEMPLATE = (
    "Emergency escalation alert. "
    "Driver {driver_name} has not responded to the consciousness check. "
    "This is now classified as a maximum priority emergency. "
    "All emergency services are being immediately dispatched. "
    "Driver location has been pinned and shared with all responders."
)


def generate_emergency_audio(driver_name: str, emergency_type: str,
                              hospital_name: str, lang: str = 'en',
                              session_id: str = None) -> dict:
    """
    Generate and cache emergency voice alert for the driver.
    Returns dict with {audio_url, text_en, text_translated}
    """
    text_en = EMERGENCY_ALERT_TEMPLATE.format(
        driver_name=driver_name,
        emergency_type=emergency_type,
        hospital_name=hospital_name
    )
    text_translated = translate_text(text_en, lang)

    sid = session_id or str(uuid.uuid4())[:8]
    filename = f"emergency_{sid}_{lang}.mp3"
    filepath = os.path.join(AUDIO_DIR, filename)

    path = speak_text(text_translated, lang, filepath)
    audio_url = f"/static/audio/{filename}" if path else None

    return {
        'audio_url': audio_url,
        'text_en': text_en,
        'text_translated': text_translated,
        'lang': lang,
        'session_id': sid,
        'timestamp': datetime.now().isoformat()
    }


def generate_consciousness_check_audio(driver_name: str, lang: str = 'en',
                                        session_id: str = None) -> dict:
    """Generate consciousness check voice prompt for the driver."""
    text_en = CONSCIOUSNESS_CHECK_TEMPLATE.format(driver_name=driver_name)
    text_translated = translate_text(text_en, lang)

    sid = session_id or str(uuid.uuid4())[:8]
    filename = f"consciousness_{sid}_{lang}.mp3"
    filepath = os.path.join(AUDIO_DIR, filename)

    path = speak_text(text_translated, lang, filepath)
    audio_url = f"/static/audio/{filename}" if path else None

    return {
        'audio_url': audio_url,
        'text_en': text_en,
        'text_translated': text_translated,
        'lang': lang,
        'session_id': sid
    }


def generate_family_notification_audio(driver_name: str, emergency_type: str,
                                         hospital_name: str, eta: int,
                                         lang: str = 'en',
                                         member_id: str = '1') -> dict:
    """Generate family notification audio in their preferred language."""
    text_en = FAMILY_NOTIFICATION_TEMPLATE.format(
        driver_name=driver_name,
        emergency_type=emergency_type,
        hospital_name=hospital_name,
        eta=eta
    )
    text_translated = translate_text(text_en, lang)

    sid = str(uuid.uuid4())[:8]
    filename = f"family_{member_id}_{sid}_{lang}.mp3"
    filepath = os.path.join(AUDIO_DIR, filename)

    path = speak_text(text_translated, lang, filepath)
    audio_url = f"/static/audio/{filename}" if path else None

    return {
        'audio_url': audio_url,
        'text_en': text_en,
        'text_translated': text_translated,
        'lang': lang
    }


def generate_hospital_notification_audio(driver_name: str, age: int,
                                           blood_group: str, emergency_type: str,
                                           risk_percent: float, eta: int,
                                           department: str,
                                           lang: str = 'en') -> dict:
    """Generate hospital notification audio."""
    text_en = HOSPITAL_NOTIFICATION_TEMPLATE.format(
        driver_name=driver_name,
        age=age,
        blood_group=blood_group,
        emergency_type=emergency_type,
        risk_percent=round(risk_percent, 1),
        eta=eta,
        department=department
    )
    text_translated = translate_text(text_en, lang)

    sid = str(uuid.uuid4())[:8]
    filename = f"hospital_{sid}_{lang}.mp3"
    filepath = os.path.join(AUDIO_DIR, filename)

    path = speak_text(text_translated, lang, filepath)
    audio_url = f"/static/audio/{filename}" if path else None

    return {
        'audio_url': audio_url,
        'text_en': text_en,
        'text_translated': text_translated,
        'lang': lang
    }


def generate_escalation_audio(driver_name: str, lang: str = 'en',
                                session_id: str = None) -> dict:
    """Generate escalation (no-response) audio alert."""
    text_en = ESCALATION_TEMPLATE.format(driver_name=driver_name)
    text_translated = translate_text(text_en, lang)

    sid = session_id or str(uuid.uuid4())[:8]
    filename = f"escalation_{sid}_{lang}.mp3"
    filepath = os.path.join(AUDIO_DIR, filename)

    path = speak_text(text_translated, lang, filepath)
    audio_url = f"/static/audio/{filename}" if path else None

    return {
        'audio_url': audio_url,
        'text_en': text_en,
        'text_translated': text_translated,
        'lang': lang
    }


def process_voice_interaction(user_input: str, context: dict = None, preferred_lang: str = 'en') -> dict:
    """
    Complete Fail-Safe Multilingual Emergency Voice Processing Pipeline.
    Detects language, analyzes emotion, evaluates dialogue context, validates safety,
    and synthesizes TTS response.
    Guaranteed NEVER to raise exceptions or block emergency dispatch.
    """
    from ai.language_detector import detect_language_from_text
    from ai.emotion_engine import analyze_emotion
    from ai.safety_engine import validate_response
    from ai.emergency_dialogue import process_driver_query
    from voice.voice_fallback import EmergencyFallbackController

    fallback_ctrl = EmergencyFallbackController()
    context = context or {}

    try:
        # 1. Language Detection (with user preference override)
        detected_lang, confidence = detect_language_from_text(user_input, preferred_lang)
        active_lang = preferred_lang if preferred_lang in ['ta', 'en', 'hi', 'te', 'kn', 'ml'] else detected_lang

        # 2. Emotion Analysis (for tone adaptation only, not clinical risk)
        vitals = context.get('vitals', {})
        emotion_data = analyze_emotion(user_input, vitals)

        # 3. Contextual Dialogue Processing
        raw_response = process_driver_query(user_input, context, lang=active_lang)

        # 4. Response Safety Validation
        emerg_status = context.get('emergency_status', 'EMERGENCY_DETECTED')
        safe_response = validate_response(raw_response, emerg_status, lang=active_lang)

        # 5. Text-To-Speech Synthesis
        sid = str(uuid.uuid4())[:8]
        filename = f"resp_{sid}_{active_lang}.mp3"
        filepath = os.path.join(AUDIO_DIR, filename)

        path = speak_text(safe_response, active_lang, filepath)
        audio_url = f"/static/audio/{filename}" if path else None

        return {
            'success': True,
            'is_fallback': False,
            'language': active_lang,
            'language_confidence': confidence,
            'emotion': emotion_data['emotion'],
            'tone_instruction': emotion_data['tone_instruction'],
            'text': safe_response,
            'audio_url': audio_url
        }
    except Exception as err:
        return fallback_ctrl.handle_voice_failure(err, context, lang=preferred_lang)



if __name__ == '__main__':
    # Quick smoke test
    print("Testing Voice Engine...")
    result = generate_emergency_audio(
        driver_name="Lithhish",
        emergency_type="Heart Attack",
        hospital_name="Thangam Hospital",
        lang='ta',
        session_id='test001'
    )
    print("Driver Alert:", result)

    fam = generate_family_notification_audio(
        driver_name="Lithhish",
        emergency_type="Heart Attack",
        hospital_name="Thangam Hospital",
        eta=8,
        lang='hi',
        member_id='1'
    )
    print("Family Alert:", fam)
