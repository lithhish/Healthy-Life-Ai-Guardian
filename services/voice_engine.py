import os
import json

# Optional Gemini Integration
try:
    import google.generativeai as genai
    HAS_GEMINI = True
except ImportError:
    HAS_GEMINI = False

class VoiceEngine:
    def __init__(self):
        self.api_key = os.environ.get('GEMINI_API_KEY')
        if self.api_key and HAS_GEMINI and self.api_key != 'your_gemini_api_key_here':
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel('gemini-pro')
        else:
            self.model = None
            
    def analyze_voice_input(self, text, driver_name="Driver", vitals=None):
        if vitals is None:
            vitals = {}
            
        return self._fallback_logic(text, driver_name, vitals)
            
    def _fallback_logic(self, text, driver_name, vitals):
        text_lower = text.lower()
        response_data = {
            "response_text": f"I have noted your input. Please drive safely.",
            "action": "NONE",
            "risk_level": "LOW"
        }
        
        # Extract vitals with defaults
        hr = vitals.get('heart_rate', 72)
        spo2 = vitals.get('spo2', 98)
        sysbp = vitals.get('blood_pressure_sys', 120)
        diabp = vitals.get('blood_pressure_dia', 80)
        temp = vitals.get('temperature', 36.8)
        sleep = vitals.get('sleep', 8)
        stress = vitals.get('stress', 2)
        fatigue = vitals.get('fatigue', 2)

        # 1. Hospital Command
        if "hospital" in text_lower:
            response_data["response_text"] = "The recommended hospital is being located. The route is displayed on your map."
            response_data["action"] = "SHOW_HOSPITALS"
            
        # 2. Ambulance Command
        elif "ambulance" in text_lower:
            response_data["response_text"] = "Ambulance dispatch is being simulated. Updating your logistics screen."
            response_data["action"] = "SHOW_AMBULANCE"
            
        # 3. Navigation Command
        elif "route" in text_lower or "navigation" in text_lower:
            response_data["response_text"] = "Opening your map route now."
            
        # 4. Family Command
        elif "family" in text_lower:
            response_data["response_text"] = "Your emergency contact notification has been prepared."
            
        # 5. General Health Check ("How am I?", "Check my health")
        elif "how am i" in text_lower or "check my health" in text_lower:
            if sysbp > 140 or hr > 100 or spo2 < 92 or temp > 38.0:
                response_data["response_text"] = "Your current simulated health readings show some abnormal values. Please review your dashboard and monitor your condition."
                response_data["risk_level"] = "MEDIUM"
            else:
                response_data["response_text"] = f"Your current simulated health readings are within the configured monitoring ranges. Your heart rate is {hr} beats per minute, oxygen is {spo2} percent, and blood pressure is {sysbp} over {diabp}. Continue monitoring and drive safely."
                
        # 6. Specific Vitals Checks
        elif "blood pressure" in text_lower:
            if sysbp > 180:
                response_data["response_text"] = "Your blood pressure reading is significantly abnormal. Please stop driving safely and seek urgent medical evaluation."
                response_data["risk_level"] = "CRITICAL"
                response_data["action"] = "TRIGGER_EMERGENCY"
            elif sysbp > 140:
                response_data["response_text"] = "Your current blood pressure reading is elevated. Please remain calm and avoid sudden exertion. If you are driving, stop at a safe location when possible."
                response_data["risk_level"] = "HIGH"
            else:
                response_data["response_text"] = "Your current blood pressure reading is within the configured monitoring range."
                
        elif "heart rate" in text_lower:
            if hr > 120:
                response_data["response_text"] = "Your heart rate is significantly elevated. Please stop the vehicle safely."
                response_data["risk_level"] = "HIGH"
            else:
                response_data["response_text"] = f"Your heart rate is {hr} beats per minute."
                
        elif "oxygen" in text_lower or "breathe" in text_lower or "breathing" in text_lower:
            if spo2 < 90:
                response_data["response_text"] = "Your oxygen saturation is critically low. Please stop the vehicle immediately."
                response_data["risk_level"] = "CRITICAL"
                response_data["action"] = "TRIGGER_EMERGENCY"
            else:
                response_data["response_text"] = f"Your oxygen saturation is {spo2} percent."
                
        elif "temperature" in text_lower or "fever" in text_lower:
            if temp > 37.5:
                response_data["response_text"] = "Your recorded temperature is elevated. Please monitor your condition and avoid continuing to drive if you feel unwell. Seek medical evaluation if symptoms are severe or worsening."
                response_data["risk_level"] = "MEDIUM"
            else:
                response_data["response_text"] = f"Your current temperature is {temp} degrees Celsius."
                
        # 7. Fatigue & Sleep
        elif "tired" in text_lower or "sleep" in text_lower or "fatigue" in text_lower or "weak" in text_lower:
            if sleep < 5:
                response_data["response_text"] = "You have reported insufficient sleep. Please take an appropriate rest break and avoid continuing to drive if you feel excessively tired."
                response_data["risk_level"] = "HIGH"
            elif fatigue > 6:
                response_data["response_text"] = "You appear to be experiencing significant fatigue. Please stop at a safe location and rest before continuing your journey."
                response_data["risk_level"] = "HIGH"
            else:
                response_data["response_text"] = "Please ensure you take regular rest breaks during long drives."
                
        # 8. Alcohol
        elif "alcohol" in text_lower or "drank" in text_lower or "drunk" in text_lower:
            response_data["response_text"] = "Alcohol-related driving risk has been detected in the current simulation. Please do not continue driving. Stop safely and arrange alternative transportation."
            response_data["risk_level"] = "CRITICAL"
            response_data["action"] = "TRIGGER_EMERGENCY"
                
        # 9. Emergency Symptoms
        elif any(word in text_lower for word in ["chest", "dizzy", "pain", "faint"]):
            response_data["response_text"] = "Your symptoms may indicate a potentially serious medical emergency. Please stop the vehicle safely. Emergency assistance is being activated."
            response_data["risk_level"] = "CRITICAL"
            response_data["action"] = "TRIGGER_EMERGENCY"
            
        # 10. Greetings
        elif text_lower in ["hi", "hello", "hi ai", "hello guardian", "hey guardian"]:
            response_data["response_text"] = f"Hello {driver_name}. I am your AI Health Guardian. How are you feeling today?"
            
        return response_data
