/**
 * AI Voice Health Assistant — Human-Like Multilingual Agentic AI
 * Languages: Tamil (ta), English (en), Hindi (hi)
 * Features:
 *   - Always-active background listening
 *   - Wake word activation: "hi" / "hello" / "வணக்கம்" / "नमस्ते"
 *   - Auto language detection from speech
 *   - Sentiment & emotion analysis
 *   - Agentic AI: takes actions, not just answers
 *   - Fully human-like conversational flow
 */

(function () {
  'use strict';

  // ─── Configuration ────────────────────────────────────────────────────────
  const WAKE_WORDS = {
    en: ['hi', 'hello', 'hey', 'guardian', 'ai guardian', 'hey guardian'],
    ta: ['வணக்கம்', 'vanakkam', 'hello', 'hi', 'ஐ', 'guardian'],
    hi: ['नमस्ते', 'namaste', 'hello', 'hi', 'haan', 'guardian', 'सहायक']
  };

  // Greetings per language — very human, warm responses
  const GREETINGS = {
    en: [
      "Hello! I'm your AI Health Guardian. How are you feeling right now? I'm here to help!",
      "Hi there! Your personal health assistant is ready. Tell me, how are you doing?",
      "Hey! Good to hear from you. I'm monitoring your health. What can I help you with?"
    ],
    ta: [
      "வணக்கம்! நான் உங்கள் AI ஆரோக்கிய காவலர். நீங்கள் எப்படி உணர்கிறீர்கள்? நான் உதவ இங்கே இருக்கிறேன்!",
      "ஹலோ! உங்கள் தனிப்பட்ட AI உதவியாளர் தயாராக இருக்கிறேன். நீங்கள் எப்படி இருக்கிறீர்கள்?",
      "வணக்கம்! நான் உங்கள் உடல் நலனை கவனிக்கிறேன். என்ன உதவி வேண்டும்?"
    ],
    hi: [
      "नमस्ते! मैं आपका AI स्वास्थ्य सहायक हूं। आप कैसा महसूस कर रहे हैं? मैं यहां आपकी मदद के लिए हूं!",
      "हेलो! आपका व्यक्तिगत स्वास्थ्य सहायक तैयार है। बताइए, आप कैसे हैं?",
      "नमस्ते! मैं आपके स्वास्थ्य पर नज़र रख रहा हूं। आप क्या जानना चाहते हैं?"
    ]
  };

  const LISTENING_PHRASES = {
    en: "I'm always here, listening... Just say 'Hi' or 'Hello' to talk to me.",
    ta: "நான் எப்போதும் இங்கே இருக்கிறேன்... பேச 'வணக்கம்' அல்லது 'ஹலோ' சொல்லுங்கள்.",
    hi: "मैं हमेशा यहां हूं... बात करने के लिए 'हेलो' या 'नमस्ते' कहें।"
  };

  const SENTIMENT_RESPONSES = {
    distressed: {
      en: "I can hear that you're not feeling well. Please stay calm — I'm here with you and help is available.",
      ta: "நீங்கள் சரியாக இல்லை என்று தெரிகிறது. அமைதியாக இருங்கள் — நான் இங்கே இருக்கிறேன், உதவி கிடைக்கும்.",
      hi: "मैं समझ सकता हूं कि आप ठीक नहीं हैं। शांत रहें — मैं यहां हूं और मदद उपलब्ध है।"
    },
    pain: {
      en: "I understand you're in pain. Tell me where it hurts and I'll get you immediate help.",
      ta: "உங்களுக்கு வலி இருப்பதை புரிந்துகொள்கிறேன். எங்கு வலிக்கிறது என்று சொல்லுங்கள், உடனடியாக உதவுகிறேன்.",
      hi: "मैं समझता हूं कि आपको दर्द हो रहा है। बताइए कहां दर्द है, मैं तुरंत मदद करूंगा।"
    },
    happy: {
      en: "Great to hear you're feeling good! I'm monitoring your vitals and everything looks fine.",
      ta: "நீங்கள் நன்றாக உணர்கிறீர்கள் என்று கேட்டு மகிழ்ச்சி! உங்கள் vitals சரியாக இருக்கிறது.",
      hi: "यह सुनकर अच्छा लगा कि आप ठीक हैं! मैं आपके vitals की निगरानी कर रहा हूं और सब ठीक दिख रहा है।"
    },
    neutral: {
      en: "I'm listening. What would you like to know about your health today?",
      ta: "நான் கேட்கிறேன். இன்று உங்கள் ஆரோக்கியத்தைப் பற்றி என்ன தெரிந்துகொள்ள வேண்டும்?",
      hi: "मैं सुन रहा हूं। आज आप अपने स्वास्थ्य के बारे में क्या जानना चाहते हैं?"
    }
  };

  // ─── State ────────────────────────────────────────────────────────────────
  let isActive = false;          // wake-word activated
  let isListening = false;       // mic open
  let isSpeaking = false;        // TTS playing
  let detectedLang = 'en';       // current language
  let recognition = null;
  let pendingInputBuffer = [];   // inputs before wake word (collect silently)
  let conversationHistory = [];  // for agentic context
  let sentimentLog = [];         // sentiment analysis log
  let wakeWordTimeout = null;    // timeout to deactivate after silence
  let retryCount = 0;

  // ─── DOM ──────────────────────────────────────────────────────────────────
  function getEl(id) { return document.getElementById(id); }

  // ─── Language Detection from Speech ──────────────────────────────────────
  function detectLangFromText(text) {
    const t = (text || '').toLowerCase();
    // Tamil Unicode
    if (/[\u0B80-\u0BFF]/.test(t)) return 'ta';
    // Hindi Unicode  
    if (/[\u0900-\u097F]/.test(t)) return 'hi';
    // Tamil transliteration keywords
    if (/\b(vanakkam|nenju|vali|enakku|irukku|unakku|amma|appa|ambulance|maruthuvamanai|kadavul)\b/.test(t)) return 'ta';
    // Hindi transliteration keywords
    if (/\b(namaste|seene|dard|aspatal|madad|bachao|mujhe|haan|nahi|kya|mera|tera|tumhara|doctor|hospital)\b/.test(t)) return 'hi';
    // Default English
    return 'en';
  }

  // ─── Sentiment Analysis ───────────────────────────────────────────────────
  function analyzeSentiment(text) {
    const t = (text || '').toLowerCase();
    
    const distressKeywords = {
      en: ['pain', 'hurt', 'chest', 'breathe', 'dizzy', 'help', 'emergency', 'dying', 'scared', 'can\'t breathe', 'numb'],
      ta: ['வலி', 'மூச்சு', 'vali', 'moochu', 'emergency', 'kaappatrunka', 'nenju', 'padattam'],
      hi: ['dard', 'seene', 'saans', 'madad', 'bachao', 'dil', 'darr', 'emergency', 'help']
    };

    const painKeywords = {
      en: ['ache', 'sore', 'burning', 'stabbing', 'throbbing', 'pressure', 'tightness'],
      ta: ['vali', 'eruchhal', 'இழுக்கிறது'],
      hi: ['dard', 'jalan', 'takleef', 'peeda']
    };

    const positiveKeywords = {
      en: ['good', 'fine', 'great', 'okay', 'well', 'better', 'healthy', 'happy'],
      ta: ['nalla', 'nallaa', 'சரி', 'நன்றாக', 'happy', 'fine'],
      hi: ['acha', 'theek', 'ठीक', 'अच्छा', 'fine', 'okay']
    };

    // Check distress (highest priority)
    const allDistress = [...distressKeywords.en, ...distressKeywords.ta, ...distressKeywords.hi];
    if (allDistress.some(kw => t.includes(kw))) {
      const severity = t.includes('can\'t') || t.includes('emergency') || t.includes('bachao') || t.includes('kaappatrunka') 
        ? 'CRITICAL' : 'HIGH';
      return { sentiment: 'distressed', severity, confidence: 0.9 };
    }

    // Check pain
    const allPain = [...painKeywords.en, ...painKeywords.ta, ...painKeywords.hi];
    if (allPain.some(kw => t.includes(kw))) {
      return { sentiment: 'pain', severity: 'MEDIUM', confidence: 0.8 };
    }

    // Check positive
    const allPositive = [...positiveKeywords.en, ...positiveKeywords.ta, ...positiveKeywords.hi];
    if (allPositive.some(kw => t.includes(kw))) {
      return { sentiment: 'happy', severity: 'LOW', confidence: 0.75 };
    }

    return { sentiment: 'neutral', severity: 'LOW', confidence: 0.5 };
  }

  // ─── TTS: Speak text in detected language ─────────────────────────────────
  function speakText(text, lang) {
    if (!text) return;
    lang = lang || detectedLang || 'en';

    // Update UI
    updateAssistantUI(text, lang, 'speaking');

    // Try server-side gTTS first for better language quality
    fetch('/api/voice/tts', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text: text, lang: lang })
    })
    .then(r => r.json())
    .then(data => {
      if (data.audio_url) {
        const audio = new Audio(data.audio_url);
        isSpeaking = true;
        updateStatusBadge('SPEAKING', '#06b6d4');
        audio.play().catch(() => fallbackBrowserTTS(text, lang));
        audio.onended = () => {
          isSpeaking = false;
          updateStatusBadge('ACTIVE', '#10b981');
          // Re-enable listening after speaking
          restartListening();
        };
      } else {
        fallbackBrowserTTS(text, lang);
      }
    })
    .catch(() => fallbackBrowserTTS(text, lang));
  }

  function fallbackBrowserTTS(text, lang) {
    if (!('speechSynthesis' in window)) return;
    window.speechSynthesis.cancel();

    const utt = new SpeechSynthesisUtterance(text);

    // Map language codes to BCP-47
    const langMap = { ta: 'ta-IN', hi: 'hi-IN', en: 'en-IN' };
    utt.lang = langMap[lang] || 'en-IN';
    utt.rate = 0.92;
    utt.pitch = 1.05;

    // Select best voice
    const voices = window.speechSynthesis.getVoices();
    const preferred = voices.find(v => v.lang === utt.lang && !v.name.includes('Google'));
    const googleVoice = voices.find(v => v.lang === utt.lang && v.name.includes('Google'));
    if (preferred) utt.voice = preferred;
    else if (googleVoice) utt.voice = googleVoice;

    utt.onstart = () => {
      isSpeaking = true;
      updateStatusBadge('SPEAKING', '#06b6d4');
    };
    utt.onend = () => {
      isSpeaking = false;
      updateStatusBadge('ACTIVE', '#10b981');
      restartListening();
    };
    utt.onerror = () => {
      isSpeaking = false;
      restartListening();
    };

    window.speechSynthesis.speak(utt);
  }

  // ─── Speech Recognition ───────────────────────────────────────────────────
  function initSpeechRecognition() {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      console.warn('[VoiceAssistant] Web Speech API not supported.');
      updateStatusBadge('NO MIC', '#ef4444');
      return null;
    }

    const rec = new SpeechRecognition();
    rec.continuous = true;
    rec.interimResults = true;
    rec.maxAlternatives = 3;
    rec.lang = 'en-IN'; // Start with Indian English, handles all 3 languages

    rec.onstart = () => {
      isListening = true;
      retryCount = 0;
      if (!isActive) {
        updateStatusBadge('STANDBY', '#64748b');
        updateAssistantUI(LISTENING_PHRASES[detectedLang] || LISTENING_PHRASES.en, detectedLang, 'standby');
      } else {
        updateStatusBadge('LISTENING', '#f59e0b');
      }
    };

    rec.onresult = (event) => {
      let finalTranscript = '';
      let interimTranscript = '';

      for (let i = event.resultIndex; i < event.results.length; i++) {
        const result = event.results[i];
        if (result.isFinal) {
          finalTranscript += result[0].transcript;
        } else {
          interimTranscript += result[0].transcript;
        }
      }

      // Show interim text in UI
      if (interimTranscript && isActive) {
        updateInputDisplay('...' + interimTranscript);
      }

      if (finalTranscript) {
        handleSpeechInput(finalTranscript.trim());
      }
    };

    rec.onerror = (event) => {
      isListening = false;
      if (event.error === 'not-allowed') {
        updateStatusBadge('MIC DENIED', '#ef4444');
        return;
      }
      if (event.error !== 'aborted') {
        // Auto-restart on errors
        setTimeout(() => restartListening(), 1000);
      }
    };

    rec.onend = () => {
      isListening = false;
      if (!isSpeaking) {
        // Always restart — we are always listening
        setTimeout(() => restartListening(), 500);
      }
    };

    return rec;
  }

  function restartListening() {
    if (isSpeaking) return;
    if (!recognition) return;
    try {
      recognition.stop();
    } catch (e) {}
    setTimeout(() => {
      try {
        recognition.start();
      } catch (e) {
        // Already started
      }
    }, 300);
  }

  // ─── Wake Word & Input Handling ───────────────────────────────────────────
  function isWakeWord(text) {
    const t = (text || '').toLowerCase().trim();
    const allWakeWords = [...WAKE_WORDS.en, ...WAKE_WORDS.ta, ...WAKE_WORDS.hi];
    return allWakeWords.some(w => t === w || t.startsWith(w + ' ') || t.endsWith(' ' + w));
  }

  function handleSpeechInput(text) {
    if (!text || text.length < 2) return;

    // Detect language from what was said
    const spokenLang = detectLangFromText(text);

    // Analyze sentiment regardless of activation
    const sentiment = analyzeSentiment(text);
    sentimentLog.push({
      text: text,
      lang: spokenLang,
      sentiment: sentiment,
      timestamp: new Date().toISOString()
    });

    // CRITICAL sentiment always triggers response even without wake word
    if (sentiment.severity === 'CRITICAL') {
      detectedLang = spokenLang;
      isActive = true;
      activateAssistant(text, spokenLang, sentiment);
      return;
    }

    // If NOT yet activated — collect input silently, wait for wake word
    if (!isActive) {
      if (isWakeWord(text)) {
        // Wake word detected!
        detectedLang = spokenLang;
        activateFromWakeWord(text, spokenLang);
      } else {
        // Silently buffer the input — don't respond yet
        pendingInputBuffer.push({ text, lang: spokenLang, sentiment, time: Date.now() });
        // Keep only last 5 silent inputs
        if (pendingInputBuffer.length > 5) pendingInputBuffer.shift();
        updateInputDisplay('[Listening silently] ' + text);
      }
      return;
    }

    // ACTIVE: process as conversation
    detectedLang = spokenLang;
    processConversation(text, spokenLang, sentiment);
  }

  function activateFromWakeWord(text, lang) {
    isActive = true;
    detectedLang = lang;

    // Flash UI to show activation
    updateStatusBadge('ACTIVATED ✨', '#8b5cf6');
    playActivationChime();

    // Check if there's context after wake word (e.g., "Hello I have chest pain")
    const textAfterWake = removeWakeWord(text, lang);
    
    if (textAfterWake && textAfterWake.length > 3) {
      // User said wake word + question together
      const sentiment = analyzeSentiment(textAfterWake);
      setTimeout(() => processConversation(textAfterWake, lang, sentiment), 300);
    } else {
      // Just a greeting — respond warmly
      const greetings = GREETINGS[lang] || GREETINGS.en;
      const greeting = greetings[Math.floor(Math.random() * greetings.length)];
      
      setTimeout(() => {
        speakText(greeting, lang);
        updateAssistantUI(greeting, lang, 'active');
        logSentimentToServer({ event: 'activated', lang, text });
      }, 200);
    }

    // Set auto-deactivation timeout (3 minutes of silence)
    resetDeactivationTimer();
  }

  function removeWakeWord(text, lang) {
    const t = text.toLowerCase().trim();
    const allWake = [...WAKE_WORDS.en, ...WAKE_WORDS.ta, ...WAKE_WORDS.hi]
      .sort((a, b) => b.length - a.length);
    for (const w of allWake) {
      if (t.startsWith(w)) {
        return text.substring(w.length).trim();
      }
    }
    return text;
  }

  function activateAssistant(text, lang, sentiment) {
    isActive = true;
    processConversation(text, lang, sentiment);
  }

  function resetDeactivationTimer() {
    if (wakeWordTimeout) clearTimeout(wakeWordTimeout);
    wakeWordTimeout = setTimeout(() => {
      isActive = false;
      updateStatusBadge('STANDBY', '#64748b');
      const msg = LISTENING_PHRASES[detectedLang] || LISTENING_PHRASES.en;
      updateAssistantUI(msg, detectedLang, 'standby');
    }, 3 * 60 * 1000); // 3 minutes
  }

  // ─── Agentic AI Conversation Processing ──────────────────────────────────
  function processConversation(text, lang, sentiment) {
    updateInputDisplay(text);
    updateStatusBadge('THINKING 🧠', '#6366f1');

    // Add to conversation history for context
    conversationHistory.push({ role: 'user', text, lang, sentiment, time: Date.now() });
    if (conversationHistory.length > 10) conversationHistory.shift();

    // Build vitals context
    const vitals = getCurrentVitals();

    fetch('/api/voice_analyze', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        text: text,
        lang: lang,
        preferred_lang: lang,
        driver_name: window.driverName || 'Driver',
        vitals: vitals,
        sentiment: sentiment,
        conversation_history: conversationHistory.slice(-5),
        pending_context: pendingInputBuffer.slice(-3)
      })
    })
    .then(r => r.json())
    .then(data => {
      // Clear pending buffer after processing
      pendingInputBuffer = [];

      // Pick response in user's language
      let responseText = data.response_text || data.response || data.message || '';
      
      // If server returns multi-language response, pick correct one
      if (data.responses && data.responses[lang]) {
        responseText = data.responses[lang];
      }

      // Log sentiment for analytics
      sentimentLog.push({
        text: text,
        lang: lang,
        sentiment: sentiment.sentiment,
        severity: sentiment.severity,
        ai_response: responseText,
        timestamp: new Date().toISOString()
      });

      // Add to conversation history
      conversationHistory.push({ role: 'ai', text: responseText, lang, time: Date.now() });

      // Update UI
      updateAssistantUI(responseText, lang, 'active');
      logSentimentToServer({ text, lang, sentiment, response: responseText });

      // Speak the response in detected language
      speakText(responseText, lang);

      // ── Agentic Actions ──
      if (data.risk_level === 'CRITICAL' || data.action === 'TRIGGER_EMERGENCY') {
        updateStatusBadge('🚨 EMERGENCY', '#ef4444');
        pulseEmergency();
        if (typeof simulateHeartAttack === 'function') {
          setTimeout(() => simulateHeartAttack(), 1500);
        } else if (typeof submitVitals === 'function') {
          setTimeout(() => submitVitals(), 1500);
        }

      } else if (data.action === 'SHOW_HOSPITALS' || data.action === 'SHOW_AMBULANCE') {
        if (typeof submitVitals === 'function') submitVitals();

      } else if (data.action === 'NAVIGATE') {
        // Open Google Maps navigation
        const navBtn = document.getElementById('nav-route-btn');
        if (navBtn && navBtn.href && navBtn.href !== '#') {
          window.open(navBtn.href, '_blank');
        }

      } else if (data.action === 'SHOW_REPORT') {
        const reportBtn = document.getElementById('download-pdf-link');
        if (reportBtn) reportBtn.click();
      }

      resetDeactivationTimer();
    })
    .catch(err => {
      console.error('[VoiceAssistant] API error:', err);
      // Fallback: respond based on sentiment
      const fallback = getSentimentFallback(sentiment, lang);
      speakText(fallback, lang);
      updateAssistantUI(fallback, lang, 'active');
      resetDeactivationTimer();
    });
  }

  function getSentimentFallback(sentiment, lang) {
    const s = sentiment.sentiment || 'neutral';
    return (SENTIMENT_RESPONSES[s] && SENTIMENT_RESPONSES[s][lang]) ||
           SENTIMENT_RESPONSES.neutral[lang] ||
           SENTIMENT_RESPONSES.neutral.en;
  }

  // ─── Vitals Context ───────────────────────────────────────────────────────
  function getCurrentVitals() {
    return {
      heart_rate: parseFloat(getEl('input-hr')?.value || 72),
      spo2: parseFloat(getEl('input-spo2')?.value || 98),
      blood_pressure_sys: parseFloat(getEl('input-sysbp')?.value || 120),
      blood_pressure_dia: parseFloat(getEl('input-diabp')?.value || 80),
      temperature: parseFloat(getEl('input-temp')?.value || 36.8),
      respiration: parseFloat(getEl('input-resp')?.value || 14),
      sleep: parseFloat(getEl('input-sleep')?.value || 8),
      stress: parseFloat(getEl('input-stress')?.value || 2),
      fatigue: parseFloat(getEl('input-fatigue')?.value || 2)
    };
  }

  // ─── UI Updates ───────────────────────────────────────────────────────────
  function updateStatusBadge(text, color) {
    const badge = getEl('ai-voice-status');
    if (badge) {
      badge.textContent = text;
      badge.style.background = color;
      badge.style.color = '#fff';
    }
  }

  function updateAssistantUI(text, lang, mode) {
    // Response text display
    const responseEl = getEl('ai-voice-response-text') ||
                       document.querySelector('#ai-voice-response span') ||
                       document.querySelector('#ai-voice-response p');
    if (responseEl) responseEl.textContent = text;

    // Lang indicator
    const langEl = getEl('ai-current-lang');
    if (langEl) {
      const langNames = { ta: '🇮🇳 தமிழ்', hi: '🇮🇳 हिन्दी', en: '🇬🇧 English' };
      langEl.textContent = langNames[lang] || langNames.en;
    }

    // Mode-based styling
    const container = getEl('ai-assistant-panel');
    if (container) {
      container.classList.remove('mode-standby', 'mode-active', 'mode-speaking', 'mode-emergency');
      container.classList.add(`mode-${mode}`);
    }
  }

  function updateInputDisplay(text) {
    const inputEl = getEl('ai-voice-input-text') ||
                    document.querySelector('#ai-voice-input span') ||
                    document.querySelector('#ai-voice-input p');
    if (inputEl) inputEl.textContent = text;
  }

  function playActivationChime() {
    try {
      const ctx = new (window.AudioContext || window.webkitAudioContext)();
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.frequency.setValueAtTime(880, ctx.currentTime);
      osc.frequency.exponentialRampToValueAtTime(1320, ctx.currentTime + 0.15);
      gain.gain.setValueAtTime(0.3, ctx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.3);
      osc.start();
      osc.stop(ctx.currentTime + 0.3);
    } catch (e) {}
  }

  function pulseEmergency() {
    const panel = getEl('ai-assistant-panel');
    if (panel) {
      panel.style.boxShadow = '0 0 30px rgba(239,68,68,0.8)';
      panel.style.borderColor = '#ef4444';
      setTimeout(() => {
        panel.style.boxShadow = '';
      }, 3000);
    }
  }

  // ─── Sentiment Logging to Server ──────────────────────────────────────────
  function logSentimentToServer(data) {
    fetch('/api/voice/sentiment-log', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    }).catch(() => {});
  }

  // ─── Public Sentiment Summary (for reception analytics) ────────────────────
  window.getVoiceAssistantSentimentLog = function () {
    return sentimentLog;
  };

  // ─── Language Switch Override ─────────────────────────────────────────────
  window.setVoiceAssistantLanguage = function (lang) {
    if (['ta', 'en', 'hi'].includes(lang)) {
      detectedLang = lang;
      if (recognition) {
        const langMap = { ta: 'ta-IN', hi: 'hi-IN', en: 'en-IN' };
        recognition.lang = langMap[lang];
        restartListening();
      }
    }
  };

  // ─── Expose manual activation for button ─────────────────────────────────
  window.activateVoiceAssistant = function () {
    isActive = true;
    const greeting = GREETINGS[detectedLang][0];
    speakText(greeting, detectedLang);
    updateAssistantUI(greeting, detectedLang, 'active');
    updateStatusBadge('ACTIVE ✨', '#10b981');
    resetDeactivationTimer();
  };

  window.stopVoiceAssistant = function () {
    window.speechSynthesis && window.speechSynthesis.cancel();
    isSpeaking = false;
    isActive = false;
    updateStatusBadge('STANDBY', '#64748b');
  };

  // ─── Bootstrap ───────────────────────────────────────────────────────────
  document.addEventListener('DOMContentLoaded', () => {
    recognition = initSpeechRecognition();

    // Wire up existing buttons if present
    const btnTalk = getEl('ai-voice-btn');
    const btnStop = getEl('ai-voice-stop');
    const btnRepeat = getEl('ai-voice-repeat');

    if (btnTalk) {
      btnTalk.addEventListener('click', () => {
        window.activateVoiceAssistant();
      });
    }

    if (btnStop) {
      btnStop.addEventListener('click', () => {
        window.stopVoiceAssistant();
      });
    }

    if (btnRepeat) {
      btnRepeat.addEventListener('click', () => {
        const last = conversationHistory.filter(m => m.role === 'ai').pop();
        if (last) speakText(last.text, last.lang || detectedLang);
      });
    }

    // Sync language selector
    const langSel = getEl('driver-language-select');
    if (langSel) {
      langSel.addEventListener('change', () => {
        window.setVoiceAssistantLanguage(langSel.value);
      });
      // Set initial lang
      if (langSel.value) detectedLang = langSel.value || 'en';
    }

    // Auto-start background listening after 1.5s
    if (recognition) {
      setTimeout(() => {
        try {
          recognition.start();
          console.log('[VoiceAssistant] Always-active background listening started.');
        } catch (e) {}
      }, 1500);
    }

    // Show initial standby message
    setTimeout(() => {
      const msg = LISTENING_PHRASES[detectedLang] || LISTENING_PHRASES.en;
      updateAssistantUI(msg, detectedLang, 'standby');
      updateStatusBadge('STANDBY', '#64748b');
    }, 1000);
  });

})();
