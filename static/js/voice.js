/**
 * AI Driver Health Guardian - Web Speech Assistant
 * Encapsulates client-side Text-to-Speech (TTS) and Speech-to-Text (STT) Recognition
 */

const VoiceAssistant = {
    // Speak a message using Web Speech API
    speak: function(text) {
        if ('speechSynthesis' in window) {
            window.speechSynthesis.cancel(); // Stop any currently playing audio
            
            const utterance = new SpeechSynthesisUtterance(text);
            utterance.rate = 0.95; // Slightly slower, more clinical pacing
            utterance.pitch = 1.0;
            
            // Attempt to fetch standard English natural-sounding voice
            const voices = window.speechSynthesis.getVoices();
            const preferredVoice = voices.find(v => v.name.includes("Google US English") || 
                                                    v.name.includes("Microsoft Zira") ||
                                                    v.lang === "en-US");
            if (preferredVoice) {
                utterance.voice = preferredVoice;
            }
            
            window.speechSynthesis.speak(utterance);
            console.log("Voice Assistant speaking: ", text);
        } else {
            console.error("Web Speech Synthesis API is not supported in this browser.");
        }
    },

    // Listen to voice commands using Speech Recognition API
    startListening: function(onResultCallback, onErrorCallback, onStartCallback, onEndCallback) {
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        if (!SpeechRecognition) {
            console.warn("Speech Recognition API is not supported in this browser.");
            if (onErrorCallback) onErrorCallback("not-supported");
            return null;
        }

        const recognizer = new SpeechRecognition();
        recognizer.continuous = false;
        recognizer.interimResults = false;
        recognizer.lang = 'en-US';

        recognizer.onstart = function() {
            console.log("Speech recognition started listening...");
            if (onStartCallback) onStartCallback();
        };

        recognizer.onresult = function(event) {
            const transcript = event.results[0][0].transcript;
            console.log("Speech Recognition Transcript:", transcript);
            if (onResultCallback) onResultCallback(transcript);
        };

        recognizer.onerror = function(event) {
            console.error("Speech Recognition Error:", event.error);
            if (onErrorCallback) onErrorCallback(event.error);
        };

        recognizer.onend = function() {
            console.log("Speech recognition session ended.");
            if (onEndCallback) onEndCallback();
        };

        try {
            recognizer.start();
            return recognizer;
        } catch (e) {
            console.error("Failed to start Speech Recognition:", e);
            if (onErrorCallback) onErrorCallback(e.message);
            return null;
        }
    }
};

// Warm up SpeechSynthesis voices array (browsers load this asynchronously)
if ('speechSynthesis' in window) {
    window.speechSynthesis.getVoices();
    window.speechSynthesis.onvoiceschanged = function() {
        window.speechSynthesis.getVoices();
    };
}
