"""
Contextual Emergency Dialogue & State Machine.
Answers driver queries using real database status across 6 languages.
"""

from typing import Dict, Any
from ai.safety_engine import get_phrase, validate_response

class EmergencyDialogueStateMachine:
    """Tracks emergency workflow state: IDLE -> EMERGENCY_DETECTED -> AMBULANCE_REQUESTED -> AMBULANCE_ACCEPTED -> HOSPITAL_ACCEPTED -> EN_ROUTE -> COMPLETED."""
    
    def __init__(self):
        self.state = 'IDLE'

    def update_state(self, new_state: str):
        valid_states = [
            'IDLE', 'EMERGENCY_DETECTED', 'AMBULANCE_REQUESTED',
            'AMBULANCE_ACCEPTED', 'HOSPITAL_ACCEPTED', 'EN_ROUTE',
            'PATIENT_HANDOVER', 'COMPLETED'
        ]
        if new_state in valid_states:
            self.state = new_state

    def get_state_announcement(self, lang: str = 'en') -> str:
        """Returns appropriate state announcement in chosen language."""
        key_map = {
            'EMERGENCY_DETECTED': 'emergency_detected',
            'AMBULANCE_REQUESTED': 'ambulance_requested',
            'AMBULANCE_ACCEPTED': 'ambulance_accepted',
            'HOSPITAL_ACCEPTED': 'hospital_accepted',
            'COMPLETED': 'consultation_completed'
        }
        key = key_map.get(self.state, 'stay_calm')
        return get_phrase(key, lang)

def process_driver_query(query_text: str, context: Dict[str, Any], lang: str = 'en') -> str:
    """
    Processes contextual questions from driver (e.g. "Where is the ambulance?", " Which hospital?")
    using authoritative database context.
    """
    if not query_text or not query_text.strip():
        return get_phrase('stay_calm', lang)

    text_lower = query_text.strip().lower()

    amb_status = context.get('ambulance_status', 'Pending')
    hosp_name = context.get('hospital_name', 'Nearest Hospital')
    hosp_status = context.get('hospital_status', 'Notified')
    emerg_status = context.get('emergency_status', 'EMERGENCY REQUESTED')

    # Query 1: Ambulance Location / Status
    if any(k in text_lower for k in ['ambulance', 'ஆம்புலன்ஸ்', 'एम्बुलेंस', 'అంబులెన్స్', 'ಆಂಬ್ಯುಲೆನ್ಸ್']):
        if amb_status in ['ACCEPTED', 'BUSY']:
            if lang == 'ta':
                return "ஆம்புலன்ஸ் உங்கள் கோரிக்கையை ஏற்றுக்கொண்டு உங்களை நோக்கி வந்து கொண்டிருக்கிறது."
            elif lang == 'hi':
                return "एम्बुलेंस ने आपका अनुरोध स्वीकार कर लिया है और आपके पास आ रही है।"
            else:
                return f"An ambulance has accepted your request and is en route. Current status: {amb_status}."
        else:
            if lang == 'ta':
                return "ஆம்புலன்ஸ் உதவி கோரப்பட்டுள்ளது. வரவேற்புக்காக காத்திருக்கிறோம்."
            else:
                return "Ambulance request has been dispatched. Waiting for driver acceptance."

    # Query 2: Hospital Info
    if any(k in text_lower for k in ['hospital', 'மருத்துவமனை', 'अस्पताल', 'ఆసుపత్రి', 'ಆಸ್ಪತ್ರೆ', 'ആശുപത്രി']):
        if lang == 'ta':
            return f"உங்களுக்காக {hosp_name} தேர்ந்தெடுக்கப்பட்டுள்ளது. அவசர பிரிவு தயாராக உள்ளது."
        elif lang == 'hi':
            return f"आपके लिए {hosp_name} को चुना गया है।"
        else:
            return f"{hosp_name} has been selected. Hospital emergency status: {hosp_status}."

    # Query 3: What should I do? / Instructions
    if any(k in text_lower for k in ['what to do', 'என்ன செய்ய', 'क्या करूं', 'ఏమి చేయాలి']):
        return get_phrase('stop_vehicle', lang)

    # General Fallback Response
    resp = get_phrase('stay_calm', lang)
    return validate_response(resp, emerg_status, lang)
