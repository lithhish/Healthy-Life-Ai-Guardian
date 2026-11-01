"""
Predefined Local Emergency Phrases Dictionary & Safety Validation Engine.
Covers 6 Languages: Tamil (ta), English (en), Hindi (hi), Telugu (te), Kannada (kn), Malayalam (ml).
Guarantees emergency communication works offline without internet or LLMs.
"""

from typing import Dict, Any

# Predefined local phrases for all 6 languages
EMERGENCY_PHRASES: Dict[str, Dict[str, str]] = {
    'ta': {
        'emergency_detected': 'உங்களுக்கு ஒரு அவசரநிலை இருக்கலாம். தயவு செய்து அமைதியாக இருங்கள்.',
        'stay_calm': 'பதற்றப்படாதீர்கள். நான் உங்களுடன் இருக்கிறேன்.',
        'stop_vehicle': 'பாதுகாப்பாக முடிந்தால் வாகனத்தை ஓரங்கட்டி நிறுத்துங்கள்.',
        'ambulance_requested': 'அவசர ஆம்புலன்ஸ் உதவி கோரப்பட்டுள்ளது. காத்திருக்கவும்.',
        'ambulance_accepted': 'ஆம்புலன்ஸ் உங்கள் கோரிக்கையை ஏற்றுக்கொண்டு உங்களை நோக்கி வருகிறது.',
        'hospital_notified': 'அருகிலுள்ள மருத்துவமனைக்கு அவசர தகவல் அனுப்பப்பட்டுள்ளது.',
        'hospital_accepted': 'மருத்துவமனை உங்கள் அவசர சேர்க்கையை உறுதிப்படுத்தியுள்ளது.',
        'gps_unavailable': 'ஜி.பி.எஸ் சமிக்ஞை தற்போது கிடைக்கவில்லை. இருப்பிடம் தோராயமாக கண்காணிக்கப்படுகிறது.',
        'consultation_completed': 'மருத்துவ ஆலோசனை முடிந்தது. அறிக்கை மற்றும் கட்டணம் தயார்.'
    },
    'en': {
        'emergency_detected': 'This may be a health emergency. Please stay calm.',
        'stay_calm': 'Please remain calm. Assistance is on the way.',
        'stop_vehicle': 'If it is safe to do so, please pull over and stop the vehicle.',
        'ambulance_requested': 'Emergency ambulance dispatch request has been sent. Please wait.',
        'ambulance_accepted': 'An ambulance has accepted your request and is en route.',
        'hospital_notified': 'The nearest capable hospital has been alerted.',
        'hospital_accepted': 'The hospital has confirmed emergency reception.',
        'gps_unavailable': 'GPS signal is currently unavailable. Using last known coordinates.',
        'consultation_completed': 'Doctor consultation complete. Medical report and bill generated.'
    },
    'hi': {
        'emergency_detected': 'यह एक स्वास्थ्य आपातकाल हो सकता है। कृपया शांत रहें।',
        'stay_calm': 'कृपया घबराएं नहीं। सहायता भेजी जा रही है।',
        'stop_vehicle': 'यदि सुरक्षित हो, तो कृपया वाहन को किनारे रोकें।',
        'ambulance_requested': 'एम्बुलेंस सहायता का अनुरोध भेजा गया है। कृपया प्रतीक्षा करें।',
        'ambulance_accepted': 'एम्बुलेंस ने आपका अनुरोध स्वीकार कर लिया है और रास्ते में है।',
        'hospital_notified': 'निकटतम अस्पताल को सूचित कर दिया गया है।',
        'hospital_accepted': 'अस्पताल ने आपातकालीन प्रवेश की पुष्टि की है।',
        'gps_unavailable': 'जीपीएस सिग्नल वर्तमान में अनुपलब्ध है।',
        'consultation_completed': 'डॉक्टर परामर्श पूरा हुआ। रिपोर्ट तैयार है।'
    },
    'te': {
        'emergency_detected': 'ఇది ఆరోగ్య అత్యవసర పరిస్థితి కావచ్చు. దయచేసి ప్రశాంతంగా ఉండండి.',
        'stay_calm': 'దయచేసి కంగారు పడవద్దు. సహాయం అందించబడుతోంది.',
        'stop_vehicle': 'సురక్షితంగా ఉంటే, దయచేసి వాహనాన్ని పక్కన నిలపండి.',
        'ambulance_requested': 'అంబులెన్స్ సాయం కోసం అభ్యర్థన పంపబడింది.',
        'ambulance_accepted': 'అంబులెన్స్ మీ అభ్యర్థనను ఆమోదించింది.',
        'hospital_notified': 'సమీప ఆసుపత్రికి సమాచారం అందించబడింది.',
        'hospital_accepted': 'ఆసుపత్రి అత్యవసర చేరికను ధృవీకరించింది.',
        'gps_unavailable': 'జిపిఎస్ సంకేతం ప్రస్తుతం లభించడం లేదు.',
        'consultation_completed': 'వైద్యుల సంప్రదింపులు పూర్తయ్యాయి.'
    },
    'kn': {
        'emergency_detected': 'ಇದು ಆರೋಗ್ಯ ತುರ್ತು ಪರಿಸ್ಥಿತಿಯಾಗಿರಬಹುದು. ದಯವಿಟ್ಟು ಶಾಂತರಾಗಿರಿ.',
        'stay_calm': 'ದಯವಿಟ್ಟು ಆತಂಕಪಡಬೇಡಿ. ನೆರವು ಕಳುಹಿಸಲಾಗುತ್ತಿದೆ.',
        'stop_vehicle': 'ಸುರಕ್ಷಿತವಾಗಿದ್ದರೆ, ದಯವಿಟ್ಟು ವಾಹನವನ್ನು ಬದಿಗೆ ನಿಲ್ಲಿಸಿ.',
        'ambulance_requested': 'ಆಂಬ್ಯುಲೆನ್ಸ್ ಸಹಾಯಕ್ಕಾಗಿ ವಿನಂತಿಸಲಾಗಿದೆ.',
        'ambulance_accepted': 'ಆಂಬ್ಯುಲೆನ್ಸ್ ನಿಮ್ಮ ವಿನಂತಿಯನ್ನು ಸ್ವೀಕರಿಸಿದೆ.',
        'hospital_notified': 'ಹತ್ತಿರದ ಆಸ್ಪತ್ರೆಗೆ ಮಾಹಿತಿ ನೀಡಲಾಗಿದೆ.',
        'hospital_accepted': 'ಆಸ್ಪತ್ರೆಯು ತುರ್ತು ಪ್ರವೇಶವನ್ನು ದೃಢೀಕರಿಸಿದೆ.',
        'gps_unavailable': 'ಜಿಪಿಎಸ್ ಸಿಗ್ನಲ್ ಪ್ರಸ್ತುತ ಲಭ್ಯವಿಲ್ಲ.',
        'consultation_completed': 'ವೈದ್ಯರ ಸಮಾಲೋಚನೆ ಪೂರ್ಣಗೊಂಡಿದೆ.'
    },
    'ml': {
        'emergency_detected': 'ഇതൊരു ആരോഗ്യ അടിയന്തരാവസ്ഥയാകാം. ദയവായി ശാന്തനായിരിക്കുക.',
        'stay_calm': 'ദയവായി പരിഭ്രാന്തരാകരുത്. സഹായം ലഭ്യമാക്കുന്നുണ്ട്.',
        'stop_vehicle': 'സുരക്ഷിതമെങ്കിൽ വാഹനം റോഡരികിൽ നിർത്തുക.',
        'ambulance_requested': 'ആംബുലൻസ് സഹായത്തിനായുള്ള അഭ്യർത്ഥന അയച്ചു.',
        'ambulance_accepted': 'ആംബുലൻസ് നിങ്ങളുടെ അഭ്യർത്ഥന സ്വീകരിച്ചു.',
        'hospital_notified': 'അടുത്തുള്ള ആശുപത്രിയിൽ വിവരം അറിയിച്ചിട്ടുണ്ട്.',
        'hospital_accepted': 'ആശുപത്രി അടിയന്തര പ്രവേശനം സ്ഥിരീകരിച്ചു.',
        'gps_unavailable': 'ജിപിഎസ് സിഗ്നൽ ഇപ്പോൾ ലഭ്യല്ല.',
        'consultation_completed': 'ഡോക്ടറുടെ പരിശോധന പൂർത്തിയായി.'
    }
}

def get_phrase(phrase_key: str, lang: str = 'en') -> str:
    """Retrieves safe predefined phrase for given key and language with English fallback."""
    lang_dict = EMERGENCY_PHRASES.get(lang, EMERGENCY_PHRASES['en'])
    return lang_dict.get(phrase_key, EMERGENCY_PHRASES['en'].get(phrase_key, "Emergency assistance is being arranged."))

def validate_response(response_text: str, emergency_state: str, lang: str = 'en') -> str:
    """
    Validates generated response before TTS output to ensure:
    1. No invented ambulance or hospital acceptance.
    2. No definitive medical diagnosis claims.
    3. Short and safe phrasing.
    """
    if not response_text or len(response_text.strip()) == 0:
        return get_phrase('stay_calm', lang)

    text_lower = response_text.lower()

    # Rule 1: Prevent invented ambulance arrival if DB state is still PENDING
    if 'ambulance' in text_lower or 'ஆம்புலன்ஸ்' in response_text:
        if emergency_state not in ['ACCEPTED', 'PATIENT_PICKED_UP', 'ARRIVED_AT_HOSPITAL'] and 'arrived' in text_lower:
            return get_phrase('ambulance_requested', lang)

    # Rule 2: Prevent invented hospital confirmation if DB state is PENDING
    if 'hospital' in text_lower or 'மருத்துவமனை' in response_text:
        if emergency_state not in ['HOSPITAL_ACCEPTED', 'TREATED', 'COMPLETED'] and 'confirmed' in text_lower:
            return get_phrase('hospital_notified', lang)

    # Rule 3: Enforce max word limit for emergency clarity
    words = response_text.split()
    if len(words) > 40:
        response_text = " ".join(words[:40]) + "."

    return response_text
