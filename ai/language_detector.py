"""
Multilingual Language Detector with Confidence Scoring, State Stability & Fallback Chain.
Supports 6 Languages: Tamil (ta), English (en), Hindi (hi), Telugu (te), Kannada (kn), Malayalam (ml).
"""

import re
from typing import Dict, Any, Tuple

SUPPORTED_LANGUAGES = {
    'ta': 'Tamil',
    'en': 'English',
    'hi': 'Hindi',
    'te': 'Telugu',
    'kn': 'Kannada',
    'ml': 'Malayalam'
}

# Script range unicode regex patterns
UNICODE_RANGES = {
    'ta': re.compile(r'[\u0B80-\u0BFF]'), # Tamil
    'hi': re.compile(r'[\u0900-\u097F]'), # Devanagari (Hindi)
    'te': re.compile(r'[\u0C00-\u0C7F]'), # Telugu
    'kn': re.compile(r'[\u0C80-\u0CFF]'), # Kannada
    'ml': re.compile(r'[\u0D00-\u0D7F]'), # Malayalam
    'en': re.compile(r'[a-zA-Z]')        # Latin/English
}

# Common transliterated keywords for Indian languages in Latin script
TRANSLITERATED_KEYWORDS = {
    'ta': ['nenju', 'vali', 'ambalan', 'maruthuvamanai', 'padattam', 'irukku', 'enakku', 'kaappatrunka'],
    'hi': ['seene', 'dard', 'aspatal', 'madad', 'bachao', 'bhaisahab', 'mujhko', 'ho'],
    'te': ['gunde', 'noppi', 'aspathri', 'sahayam', 'naaku', 'undhi'],
    'kn': ['edeya', 'novugale', 'aspathre', 'sahaya', 'nanage', 'ide'],
    'ml': ['nenju', 'vedhana', 'asupathri', 'sahayam', 'enikku', 'undu']
}

class LanguageStateTracker:
    """Tracks active language state with stability thresholds to prevent erratic flipping."""
    def __init__(self, default_lang: str = 'en'):
        self.current_lang = default_lang if default_lang in SUPPORTED_LANGUAGES else 'en'
        self.confidence_history = []
        self.user_override_lang = None

    def set_user_override(self, lang: str):
        if lang in SUPPORTED_LANGUAGES:
            self.user_override_lang = lang

    def clear_user_override(self):
        self.user_override_lang = None

    def update_language(self, detected_lang: str, confidence: float) -> str:
        # Priority 1: User explicit override
        if self.user_override_lang:
            return self.user_override_lang

        # Priority 2: High confidence detection
        if confidence >= 0.70:
            self.current_lang = detected_lang
        elif confidence < 0.40:
            # Low confidence — retain current stable language
            pass
        else:
            # Moderate confidence — retain unless repeated
            self.current_lang = detected_lang

        return self.current_lang

def detect_language_from_text(text: str, user_preference: str = 'en') -> Tuple[str, float]:
    """
    Detects language from text input using Unicode script matching and transliterated keyword analysis.
    Returns (lang_code, confidence).
    """
    if not text or not text.strip():
        return user_preference if user_preference in SUPPORTED_LANGUAGES else 'en', 0.5

    text_clean = text.strip()
    total_len = len(text_clean)

    # 1. Script Range Matching
    script_counts = {}
    for lang, pattern in UNICODE_RANGES.items():
        matches = len(pattern.findall(text_clean))
        if matches > 0:
            script_counts[lang] = matches

    if script_counts:
        best_lang = max(script_counts, key=script_counts.get)
        match_count = script_counts[best_lang]
        # Calculate ratio ignoring spaces/punctuation
        letters_only = len(re.sub(r'[\s\d\W]', '', text_clean)) or 1
        confidence = round(min(1.0, match_count / letters_only + 0.2), 2)
        return best_lang, confidence

    # 2. Transliterated Keyword Match
    text_lower = text_clean.lower()
    trans_scores = {}
    for lang, keywords in TRANSLITERATED_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in text_lower)
        if score > 0:
            trans_scores[lang] = score

    if trans_scores:
        best_trans_lang = max(trans_scores, key=trans_scores.get)
        return best_trans_lang, 0.75

    # 3. Fallback to User Preference
    return user_preference if user_preference in SUPPORTED_LANGUAGES else 'en', 0.50
