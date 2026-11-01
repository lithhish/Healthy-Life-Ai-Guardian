"""
Central Emergency Fallback Controller.
Guarantees emergency notifications and voice updates continue even when speech recognition,
translation, TTS, or network connections fail completely.
"""

import os
import logging
from typing import Dict, Any
from ai.safety_engine import get_phrase

logger = logging.getLogger(__name__)

class EmergencyFallbackController:
    """Manages system fallbacks so AI failures NEVER block emergency workflow."""
    
    def __init__(self):
        self.fallback_count = 0
        self.last_error = None

    def handle_voice_failure(self, error: Exception, context: Dict[str, Any], lang: str = 'en') -> Dict[str, Any]:
        """
        Handles speech/voice pipeline errors gracefully without raising exceptions.
        Returns safe fallback voice response.
        """
        self.fallback_count += 1
        self.last_error = str(error)
        logger.warning(f"[FallbackController] Voice failure recorded ({error}). Using safe local fallback phrase.")

        emerg_state = context.get('emergency_status', 'EMERGENCY_DETECTED')
        fallback_text = get_phrase('stay_calm', lang)

        return {
            'success': True,
            'is_fallback': True,
            'language': lang,
            'text': fallback_text,
            'emotion': 'CALM',
            'audio_url': None, # Web Speech API / Visual fallback
            'error_logged': str(error)
        }

    def handle_stt_failure(self, error: Exception) -> Dict[str, Any]:
        """Handles speech-to-text failure cleanly."""
        logger.warning(f"[FallbackController] STT failure: {error}")
        return {
            'success': False,
            'is_fallback': True,
            'text': '',
            'message': 'Voice recognition unavailable. Please use touch controls.'
        }
