"""
Emotion & Sentiment Analysis Engine.
Classifies user emotional state (CALM, ANXIOUS, PANICKED, CONFUSED, DISTRESSED, URGENT, UNKNOWN).
NOTE: Emotion is used EXCLUSIVELY for conversational tone adaptation — NOT for medical risk diagnosis.
"""

import re
from typing import Dict, Any

EMOTION_PATTERNS = {
    'PANICKED': [
        r'\bhelp\b', r'\bplease help\b', r'\bscared\b', r'\bterrified\b', r'\bdying\b',
        r'காப்பாற்றுங்கள்', r'பயமாக இருக்கிறது', r'பதற்றமாக இருக்கிறது',
        r'बचाओ', r'डर लग रहा है', r'காப்பாத்துங்க'
    ],
    'ANXIOUS': [
        r'\bworried\b', r'\bafraid\b', r'\bnervous\b', r'\bchest tightness\b',
        r'பயம்', r'கவலை', r'चिंता', r'घबराहट'
    ],
    'CONFUSED': [
        r'\bwhat is happening\b', r'\bdon\'t know\b', r'\bwhere am i\b', r'\bwhat to do\b',
        r'என்ன நடக்கிறது', r'என்ன செய்வது', r'क्या करूं', r'समझ नहीं आ रहा'
    ],
    'DISTRESSED': [
        r'\bsevere pain\b', r'\bcannot breathe\b', r'\bcan\'t breathe\b', r'\bunbearable\b',
        r'கடுமையான வலி', r'மூச்சு திணறல்', r'बहुत दर्द', r'सांस नहीं आ रही'
    ],
    'URGENT': [
        r'\bquick\b', r'\bhurry\b', r'\bfast\b', r'\bimmediately\b',
        r'சீக்கிரம்', r'விரைவாக', r'जल्दी'
    ]
}

def analyze_emotion(text: str, vitals: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Analyzes emotional state from text & optional acoustic/telemetry flags.
    Returns dict with emotion, confidence, and source.
    """
    if not text or not text.strip():
        return {
            'emotion': 'UNKNOWN',
            'confidence': 0.50,
            'source': 'fallback',
            'tone_instruction': 'Use neutral, reassuring, calm voice.'
        }

    text_lower = text.strip().lower()

    for emotion, patterns in EMOTION_PATTERNS.items():
        for pat in patterns:
            if re.search(pat, text_lower, re.IGNORECASE):
                return {
                    'emotion': emotion,
                    'confidence': 0.85,
                    'source': 'nlp_keyword_matching',
                    'tone_instruction': get_tone_instruction(emotion)
                }

    # Check for acoustic vitals indicators (e.g. extreme tachypnea / tachycardia)
    if vitals:
        hr = vitals.get('heart_rate', 75)
        resp = vitals.get('respiration_rate', 16)
        if hr > 130 or resp > 28:
            return {
                'emotion': 'ANXIOUS',
                'confidence': 0.70,
                'source': 'telemetry_vitals',
                'tone_instruction': get_tone_instruction('ANXIOUS')
            }

    return {
        'emotion': 'CALM',
        'confidence': 0.80,
        'source': 'default_calm',
        'tone_instruction': get_tone_instruction('CALM')
    }

def get_tone_instruction(emotion: str) -> str:
    """Returns tone instruction for dialogue adaptation."""
    instructions = {
        'PANICKED': 'Speak in extremely reassuring, steady, short sentences. Tell driver to stop safely and breathe.',
        'ANXIOUS': 'Speak calmly and clearly, breaking down instructions into simple step-by-step guidance.',
        'CONFUSED': 'Provide direct, singular instructions without jargon.',
        'DISTRESSED': 'Acknowledge discomfort calmly, prioritize emergency arrival status updates.',
        'URGENT': 'Deliver concise, high-priority status updates immediately.',
        'CALM': 'Speak professionally, warmly, and clearly.',
        'UNKNOWN': 'Use a neutral, clear, supportive tone.'
    }
    return instructions.get(emotion, instructions['UNKNOWN'])
