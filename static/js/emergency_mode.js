/**
 * AI Driver Health Guardian — Emergency Mode Controller
 * Handles auto-emergency workflow, voice playback, consciousness check, and timeline updates
 */

const EmergencyMode = (function () {
  'use strict';

  // ── State ────────────────────────────────────────────────────────────────
  let currentEmergencyId = null;
  let sessionData        = null;
  let consciousnessTimer = null;
  let pollingInterval    = null;
  let isActive           = false;
  let audioQueue         = [];
  let consciousnessTimeout = 30; // seconds

  const POLL_INTERVAL_MS  = 3000;  // 3 s
  const CONSCIOUSNESS_SECONDS = 30;

  // ── DOM helpers ──────────────────────────────────────────────────────────
  const $ = (id) => document.getElementById(id);
  const setText = (id, text) => { if ($(id)) $(id).textContent = text; };
  const setHTML = (id, html) => { if ($(id)) $(id).innerHTML  = html;  };
  const show    = (id) => { if ($(id)) $(id).style.display = ''; };
  const hide    = (id) => { if ($(id)) $(id).style.display = 'none'; };

  // ── Entry point: called by dashboard.js after AI prediction ─────────────
  async function activateEmergency(predictionResult, vitalsData, driverLat, driverLng) {
    if (isActive) return; // Prevent double-trigger
    isActive = true;

    console.log('[EmergencyMode] Activating emergency workflow...', predictionResult);

    // 1. Show emergency overlay immediately
    _showEmergencyOverlay(predictionResult);

    // 2. Play browser alert sound (disabled per request)
    // _playAlertSound();

    // 3. Trigger server-side emergency engine
    try {
      const response = await fetch('/api/emergency/trigger', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          prediction: predictionResult,
          vitals:     vitalsData,
          lat:        driverLat,
          lng:        driverLng
        })
      });

      if (!response.ok) {
        const errData = await response.json();
        console.error('[EmergencyMode] Trigger failed:', errData);
        _handleTriggerError(errData, predictionResult);
        return;
      }

      sessionData        = await response.json();
      currentEmergencyId = sessionData.emergency_id;

      console.log('[EmergencyMode] Session created:', sessionData);

      // 4. Update overlay with full session data
      _updateOverlayWithSessionData(sessionData);

      // 5. Play driver voice alert
      if (sessionData.voice?.driver_alert_url) {
        await _playAudio(sessionData.voice.driver_alert_url, 1500);
      } else {
        _speakBrowserTTS(sessionData.voice?.driver_alert_text || _defaultAlertText(predictionResult));
      }

      // 6. Show consciousness check after voice ends
      setTimeout(() => {
        _showConsciousnessCheck();
      }, 8000);

      // 7. Start polling for live status updates
      _startPolling();

    } catch (err) {
      console.error('[EmergencyMode] Network error:', err);
      _handleTriggerError({ error: err.message }, predictionResult);
    }
  }

  // ── Emergency Overlay ───────────────────────────────────────────────────
  function _showEmergencyOverlay(prediction) {
    // Remove existing overlay if any
    const existing = document.getElementById('em-overlay');
    if (existing) existing.remove();

    const severityColor = {
      'Critical': '#ef4444', 'High': '#f97316',
      'Moderate': '#eab308', 'Low': '#06b6d4', 'Normal': '#10b981'
    }[prediction.severity] || '#ef4444';

    const overlay = document.createElement('div');
    overlay.id = 'em-overlay';
    overlay.innerHTML = `
      <div style="
        position:fixed; top:0; left:0; width:100%; height:100%; z-index:10000;
        background:rgba(10,14,26,0.97); display:flex; flex-direction:column;
        align-items:center; justify-content:center; padding:20px;
        animation:emergencyFadeIn 0.4s ease-out;">

        <!-- Pulsing ring -->
        <div style="position:relative; width:120px; height:120px; margin-bottom:24px;">
          <div style="position:absolute; inset:0; border-radius:50%; border:3px solid ${severityColor};
                      animation:sonarRing 1.2s ease-out infinite;"></div>
          <div style="position:absolute; inset:10px; border-radius:50%; border:2px solid ${severityColor};
                      animation:sonarRing 1.2s ease-out infinite 0.4s;"></div>
          <div style="position:absolute; inset:0; border-radius:50%; background:rgba(${severityColor === '#ef4444' ? '239,68,68' : '249,115,22'},0.1);
                      display:flex; align-items:center; justify-content:center;">
            <i class="fa fa-triangle-exclamation" style="font-size:2.5rem; color:${severityColor};"></i>
          </div>
        </div>

        <!-- Header -->
        <h2 style="color:${severityColor}; font-weight:900; letter-spacing:3px; margin-bottom:4px; text-align:center;">
          🚨 EMERGENCY MODE ACTIVE
        </h2>
        <div style="color:#94a3b8; font-size:0.9rem; margin-bottom:20px; text-align:center;" id="em-session-id">
          Initializing emergency session...
        </div>

        <!-- Emergency Classification -->
        <div style="background:rgba(${severityColor === '#ef4444' ? '239,68,68' : '249,115,22'},0.1);
                    border:1px solid ${severityColor}; border-radius:12px; padding:16px 24px;
                    text-align:center; max-width:500px; width:100%; margin-bottom:16px;">
          <div style="color:#94a3b8; font-size:0.75rem; text-transform:uppercase; letter-spacing:2px;">AI DETECTED</div>
          <div style="color:#fff; font-size:1.4rem; font-weight:800; margin:4px 0;" id="em-type">${prediction.prediction}</div>
          <div style="display:flex; justify-content:center; gap:16px; margin-top:8px;">
            <div>
              <div style="color:#94a3b8; font-size:0.7rem;">Severity</div>
              <div style="color:${severityColor}; font-weight:700;">${prediction.severity}</div>
            </div>
            <div>
              <div style="color:#94a3b8; font-size:0.7rem;">AI Confidence</div>
              <div style="color:#fff; font-weight:700;">${Math.round(prediction.confidence * 100)}%</div>
            </div>
            <div>
              <div style="color:#94a3b8; font-size:0.7rem;">Risk Score</div>
              <div style="color:${severityColor}; font-weight:700;">${prediction.risk_percentage}%</div>
            </div>
          </div>
        </div>

        <!-- Speaking Indicator -->
        <div id="em-speaking" style="display:flex; align-items:center; gap:8px; margin-bottom:16px; color:#06b6d4;">
          <div style="display:flex; gap:3px; align-items:center;">
            <div class="wave-bar" style="height:12px;"></div>
            <div class="wave-bar" style="height:20px;animation-delay:0.1s"></div>
            <div class="wave-bar" style="height:16px;animation-delay:0.2s"></div>
            <div class="wave-bar" style="height:24px;animation-delay:0.15s"></div>
            <div class="wave-bar" style="height:14px;animation-delay:0.25s"></div>
          </div>
          <span style="font-size:0.85rem;" id="em-speaking-text">AI Voice Assistant speaking...</span>
        </div>

        <!-- Status Cards Row -->
        <div style="display:flex; flex-wrap:wrap; gap:10px; justify-content:center; max-width:600px; width:100%; margin-bottom:20px;">
          <div class="em-status-card" id="em-card-hospital">
            <i class="fa fa-hospital"></i><span id="em-hospital-text">Finding hospital...</span>
          </div>
          <div class="em-status-card" id="em-card-ambulance">
            <i class="fa fa-truck-medical"></i><span id="em-ambulance-text">Dispatching ambulance...</span>
          </div>
          <div class="em-status-card" id="em-card-family">
            <i class="fa fa-users"></i><span id="em-family-text">Notifying family...</span>
          </div>
        </div>

        <!-- Consciousness Check Panel (hidden initially) -->
        <div id="em-consciousness-panel" style="display:none; background:rgba(6,182,212,0.08);
             border:1px solid rgba(6,182,212,0.4); border-radius:12px; padding:20px;
             max-width:500px; width:100%; text-align:center; margin-bottom:16px;">
          <div style="color:#06b6d4; font-weight:700; margin-bottom:8px;">
            <i class="fa fa-ear-listen me-2"></i>CONSCIOUSNESS CHECK
          </div>
          <p style="color:#e2e8f0; font-size:0.9rem; margin-bottom:12px;" id="em-check-question">
            Can you hear me? Are you conscious? Please respond within <span id="em-countdown" style="color:#fbbf24; font-weight:800;">30</span> seconds.
          </p>
          <div style="display:flex; gap:10px; justify-content:center; flex-wrap:wrap;">
            <button onclick="EmergencyMode.respondConscious()" style="
              background:linear-gradient(135deg,#10b981,#059669); border:none; color:#fff;
              padding:10px 24px; border-radius:8px; font-weight:700; font-size:0.9rem; cursor:pointer;">
              <i class="fa fa-check-circle me-1"></i> Yes, I Can Hear You
            </button>
            <button onclick="EmergencyMode.respondNeedHelp()" style="
              background:rgba(239,68,68,0.2); border:1px solid #ef4444; color:#ef4444;
              padding:10px 24px; border-radius:8px; font-weight:700; font-size:0.9rem; cursor:pointer;">
              <i class="fa fa-hand-holding-medical me-1"></i> I Need Help
            </button>
          </div>
        </div>

        <!-- Action Buttons -->
        <div style="display:flex; gap:12px; flex-wrap:wrap; justify-content:center;">
          <a id="em-maps-btn" href="#" target="_blank" style="display:none;
             background:linear-gradient(135deg,#3b82f6,#6366f1); color:#fff;
             padding:10px 20px; border-radius:8px; text-decoration:none; font-weight:600; font-size:0.85rem;">
            <i class="fa fa-map-location-dot me-1"></i>Open Navigation
          </a>
          <a id="em-report-btn" href="#" style="display:none;
             background:rgba(99,102,241,0.2); border:1px solid rgba(99,102,241,0.5); color:#a5b4fc;
             padding:10px 20px; border-radius:8px; text-decoration:none; font-weight:600; font-size:0.85rem;">
            <i class="fa fa-file-pdf me-1"></i>Download Report
          </a>
          <button onclick="EmergencyMode.dismiss()" style="
            background:rgba(100,116,139,0.2); border:1px solid rgba(100,116,139,0.4); color:#94a3b8;
            padding:10px 20px; border-radius:8px; font-weight:600; font-size:0.85rem; cursor:pointer;">
            <i class="fa fa-times me-1"></i>Dismiss
          </button>
        </div>

        <!-- Timeline -->
        <div id="em-timeline-container" style="max-width:500px; width:100%; margin-top:16px; text-align:left;">
          <div style="color:#64748b; font-size:0.72rem; text-transform:uppercase; letter-spacing:1px; margin-bottom:8px;">
            Emergency Timeline
          </div>
          <div id="em-timeline-list"></div>
        </div>
      </div>`;

    document.body.appendChild(overlay);

    // Add wave bar and overlay styles
    const style = document.createElement('style');
    style.textContent = `
      @keyframes emergencyFadeIn { from{opacity:0;transform:scale(0.95)} to{opacity:1;transform:scale(1)} }
      @keyframes sonarRing { 0%{transform:scale(1);opacity:0.8} 100%{transform:scale(1.5);opacity:0} }
      @keyframes waveAnim { 0%,100%{transform:scaleY(0.5)} 50%{transform:scaleY(1)} }
      .wave-bar {
        width:4px; background:#06b6d4; border-radius:2px;
        animation:waveAnim 0.8s ease-in-out infinite;
        display:inline-block;
      }
      .em-status-card {
        background:rgba(255,255,255,0.04); border:1px solid rgba(255,255,255,0.1);
        border-radius:8px; padding:8px 14px; display:flex; align-items:center; gap:8px;
        font-size:0.78rem; color:#94a3b8; white-space:nowrap;
      }
      .em-status-card i { color:#06b6d4; }
      .em-status-card.done { border-color:#10b981; color:#10b981; }
      .em-status-card.done i { color:#10b981; }
      .em-status-card.fail { border-color:#ef4444; color:#ef4444; }
      .em-status-card.fail i { color:#ef4444; }
      .em-status-card.calling { border-color:#fbbf24; color:#fbbf24; }
      .em-status-card.calling i { color:#fbbf24; }
      .em-status-card.skipped { border-color:#64748b; color:#64748b; }
      .em-status-card.skipped i { color:#64748b; }
    `;
    document.head.appendChild(style);
  }

  function _updateOverlayWithSessionData(data) {
    const emgCode = data.session_id || data.emergency_id || (data.emergency_db_id ? `EMG-${String(data.emergency_db_id).padStart(6,'0')}` : '---');
    setText('em-session-id', `Emergency ID: ${emgCode} | ${(data.timestamp||'').slice(0,16)}`);

    const emgId = data.emergency_db_id || data.emergency_id || data.id;
    if (emgId) {
      const reportBtn = $('em-report-btn');
      if (reportBtn) {
        reportBtn.href = `/api/reports/download/${emgId}?t=${Date.now()}`;
        reportBtn.style.display = '';
      }
    }

    // ── Show hospital info immediately ──────────────────────────────────
    const hosp = data.hospital || data.assigned_hospital || { name: 'Lotus Hospital & Research Centre', distance_km: 2.4, eta_min: 8 };
    const hospName = hosp.name || hosp.hospital_name || 'Lotus Hospital';
    const cardH = $('em-card-hospital');
    if (cardH) {
      setText('em-hospital-text', `${hospName} (${hosp.distance_km || 2.4} km, ETA ${hosp.eta_min || hosp.travel_time_min || 8} min)`);
      cardH.className = 'em-status-card done';
    }

    // ── Show ambulance info immediately ─────────────────────────────────
    const amb = data.ambulance || data.assigned_ambulance || { vehicle_number: 'TN-33-AMB-108', driver_name: 'SANTHOSH S', eta_min: 5 };
    const ambVeh = amb.vehicle || amb.vehicle_number || 'TN-33-AMB-108';
    const ambDriver = amb.driver || amb.driver_name || 'SANTHOSH S';
    const cardA = $('em-card-ambulance');
    if (cardA) {
      setText('em-ambulance-text', `${ambVeh} — Driver: ${ambDriver} (ETA ${amb.eta_min || amb.eta_minutes || 5} min)`);
      cardA.className = 'em-status-card done';
    }

    // ── Show family alert info immediately ───────────────────────────────
    const cardF = $('em-card-family');
    if (cardF) {
      setText('em-family-text', 'Family Alerted via SMS & Call');
      cardF.className = 'em-status-card done';
    }


    // ── Enable navigation map button ─────────────────────────────────────
    if (hosp && (hosp.maps_url || (hosp.latitude && hosp.longitude))) {
      const mapsBtn = $('em-maps-btn');
      if (mapsBtn) {
        mapsBtn.href = hosp.maps_url || `https://www.google.com/maps/dir/?api=1&destination=${hosp.latitude},${hosp.longitude}`;
        mapsBtn.style.display = '';
      }
    }

    // ── Activate driver dashboard flow steps ─────────────────────────────
    _markDashboardStep('step-vitals', 'completed');
    _markDashboardStep('step-prediction', 'completed');
    _markDashboardStep('step-voice', 'completed');
    _markDashboardStep('step-hospital', 'completed');
    _markDashboardStep('step-ambulance', 'completed');
    _markDashboardStep('step-family', 'completed');
    _markDashboardStep('step-hospital-notified', 'completed');
    _markDashboardStep('step-report', 'completed');

    // ── Show hospital/ambulance info box in driver dashboard ─────────────
    _updateDriverDashboardInfoBox(data);
  }

  function _markDashboardStep(stepId, cls) {
    const el = document.getElementById(stepId);
    if (el) { el.classList.remove('active','completed'); el.classList.add(cls); }
  }

  function _updateDriverDashboardInfoBox(data) {
    const hosp = data.hospital || data.assigned_hospital || {};
    const amb  = data.ambulance || data.assigned_ambulance || {};

    const hospName = hosp.name || 'Government Medical College Hospital, Perundurai';
    const hospAddr = hosp.address || 'Kochi - Salem Highway, Perundurai, Erode';
    const hospPhone = hosp.phone || hosp.emergency_number || '+91 4294 220 200';
    const hospDist = hosp.distance_km || 2.4;

    const ambVeh = amb.vehicle_number || amb.vehicle || 'TN-33-AMB-108';
    const ambDriver = amb.driver_name || amb.driver || 'SANTHOSH S';
    const ambPhone = amb.driver_phone || amb.phone || '+91 9943064577';
    const ambEta = amb.eta_minutes || amb.eta_min || 5;

    const emgId = data.emergency_db_id || data.emergency_id || data.id;

    setText('hosp-name', hospName);
    setText('hosp-address', hospAddr);
    setText('hosp-phone', hospPhone);
    setText('hosp-distance', hospDist + ' km');

    setText('amb-veh', ambVeh);
    setText('amb-driver', ambDriver);
    setText('amb-phone', ambPhone);
    setText('amb-eta', ambEta + ' mins');

    const downloadContainer = document.getElementById('download-report-btn');
    if (downloadContainer) {
      downloadContainer.style.display = 'block';
      const downloadLink = document.getElementById('download-pdf-link');
      if (downloadLink && emgId) {
        downloadLink.href = `/api/reports/download/${emgId}`;
      }
    }

    const navBtn = document.getElementById('nav-route-btn');
    if (navBtn) {
      const mapsUrl = hosp.maps_url || `https://www.google.com/maps/dir/?api=1&destination=${hosp.latitude || 11.275},${hosp.longitude || 77.585}`;
      navBtn.style.display = 'inline-block';
      navBtn.href = mapsUrl;
      navBtn.dataset.mapsUrl = mapsUrl;
      // Direct navigation on click — no extra step required
      navBtn.onclick = function(e) {
        e.preventDefault();
        window.open(mapsUrl, '_blank', 'noopener,noreferrer');
      };
    }

    let infoBox = document.getElementById('em-matched-info-box');
    if (!infoBox) {
      infoBox = document.createElement('div');
      infoBox.id = 'em-matched-info-box';
      infoBox.style.cssText = 'margin:12px 0;padding:12px 16px;border-radius:8px;background:rgba(16,185,129,0.08);border:1px solid rgba(16,185,129,0.4);display:flex;flex-wrap:wrap;gap:16px;font-size:0.82rem;';
      const timelineC = $('em-timeline-container');
      if (timelineC && timelineC.parentNode) {
        timelineC.parentNode.insertBefore(infoBox, timelineC);
      }
    }
    infoBox.innerHTML = `
      <div>
        <div style="color:#94a3b8;font-size:0.7rem;text-transform:uppercase;letter-spacing:1px;">🏥 Matched Hospital</div>
        <div style="color:#10b981;font-weight:700;">${hospName}</div>
        <div style="color:#64748b;">${hospDist} km · ETA ${hosp.eta_min || hosp.travel_time_min || 8} min</div>
      </div>
      <div>
        <div style="color:#94a3b8;font-size:0.7rem;text-transform:uppercase;letter-spacing:1px;">🚑 Dispatched Ambulance</div>
        <div style="color:#fbbf24;font-weight:700;">${ambVeh}</div>
        <div style="color:#64748b;">Driver: ${ambDriver} · ETA ${ambEta} min</div>
      </div>
    `;
  }


  // ── Consciousness Check ─────────────────────────────────────────────────
  function _showConsciousnessCheck() {
    const panel = $('em-consciousness-panel');
    if (!panel) return;
    panel.style.display = '';

    let countdown = CONSCIOUSNESS_SECONDS;
    setText('em-countdown', countdown);

    consciousnessTimer = setInterval(() => {
      countdown--;
      setText('em-countdown', countdown);
      if (countdown <= 0) {
        clearInterval(consciousnessTimer);
        _escalateEmergency();
      }
    }, 1000);

    // Play consciousness check audio
    if (sessionData?.voice?.consciousness_check_url) {
      _playAudio(sessionData.voice.consciousness_check_url, 0);
    }
  }

  function respondConscious() {
    clearInterval(consciousnessTimer);
    if (currentEmergencyId) {
      fetch(`/api/emergency/${currentEmergencyId}/consciousness`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ response: 'conscious' })
      });
    }
    const panel = $('em-consciousness-panel');
    if (panel) {
      panel.innerHTML = `
        <div style="color:#10b981; text-align:center; padding:12px;">
          <i class="fa fa-check-circle" style="font-size:2rem;"></i>
          <p class="mt-2 mb-0" style="font-weight:600;">Good! You are conscious. Help is on the way.</p>
          <p class="small text-secondary mt-1">Stay calm. Stop driving safely if you haven't already.</p>
        </div>`;
    }
  }

  function respondNeedHelp() {
    clearInterval(consciousnessTimer);
    _escalateEmergency();
  }

  function _escalateEmergency() {
    if (currentEmergencyId) {
      fetch(`/api/emergency/${currentEmergencyId}/consciousness`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ response: 'no_response' })
      });
    }
    const panel = $('em-consciousness-panel');
    if (panel) {
      panel.innerHTML = `
        <div style="color:#ef4444; text-align:center; padding:12px; animation:emergencyFadeIn 0.3s;">
          <i class="fa fa-circle-exclamation" style="font-size:2rem;"></i>
          <p class="mt-2 mb-0" style="font-weight:700; color:#ef4444;">EMERGENCY ESCALATED</p>
          <p class="small" style="color:#94a3b8; margin-top:4px;">
            No response detected. All emergency services are on maximum alert.
          </p>
        </div>`;
    }
  }

  // ── Audio Playback ───────────────────────────────────────────────────────
  async function _playAudio(url, delayMs = 0) {
    return new Promise((resolve) => {
      setTimeout(() => {
        const audio = new Audio(url);
        audio.onended = resolve;
        audio.onerror = () => {
          console.warn('[EmergencyMode] Audio playback failed, trying TTS fallback');
          resolve();
        };
        audio.play().catch((e) => {
          console.warn('[EmergencyMode] Audio play blocked:', e.message);
          resolve();
        });
      }, delayMs);
    });
  }

  function _speakBrowserTTS(text) {
    if (!('speechSynthesis' in window)) return;
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.rate = 0.85;
    utterance.pitch = 1.0;
    utterance.volume = 1.0;
    window.speechSynthesis.cancel();
    window.speechSynthesis.speak(utterance);
  }

  function _playAlertSound() {
    // Try to play beep — browser may block without user interaction
    const ctx = window.AudioContext || window.webkitAudioContext;
    if (!ctx) return;
    try {
      const audioCtx = new ctx();
      const oscillator = audioCtx.createOscillator();
      const gainNode   = audioCtx.createGain();
      oscillator.connect(gainNode);
      gainNode.connect(audioCtx.destination);
      oscillator.type = 'sine';
      oscillator.frequency.setValueAtTime(880, audioCtx.currentTime);
      gainNode.gain.setValueAtTime(0.3, audioCtx.currentTime);
      gainNode.gain.exponentialRampToValueAtTime(0.001, audioCtx.currentTime + 0.8);
      oscillator.start(audioCtx.currentTime);
      oscillator.stop(audioCtx.currentTime + 0.8);
    } catch (e) {}
  }

  // ── Live Polling ─────────────────────────────────────────────────────────
  function _startPolling() {
    if (!currentEmergencyId) return;
    pollingInterval = setInterval(_pollStatus, POLL_INTERVAL_MS);
  }

  async function _pollStatus() {
    if (!currentEmergencyId) return;
    try {
      const res  = await fetch(`/api/emergency/${currentEmergencyId}/status`);
      const data = await res.json();
      _updateTimeline(data.timeline || []);
    } catch (e) {}
  }

  function _updateTimeline(timeline) {
    const container = $('em-timeline-list');
    if (!container) return;
    container.innerHTML = timeline.slice(-8).map(step => `
      <div style="display:flex; gap:8px; align-items:flex-start; margin:4px 0; font-size:0.75rem;">
        <div style="width:8px; height:8px; border-radius:50%; margin-top:4px; flex-shrink:0;
                    background:${step.status === 'FAILED' ? '#ef4444' : (step.status === 'CALLING' || step.status === 'warning') ? '#fbbf24' : '#10b981'};"></div>
        <div>
          <span style="color:#e2e8f0; font-weight:600;">${_formatStep(step.step)}</span>
          <span style="color:#94a3b8; font-weight:700; margin-left:6px; font-size:0.7rem; text-transform:uppercase;">[${step.status}]</span>
          <span style="color:#64748b; margin-left:6px;">${step.timestamp?.slice(11,19) || ''}</span>
          ${step.detail ? `<div style="color:#94a3b8; margin-top:1px;">${step.detail.slice(0, 80)}</div>` : ''}
        </div>
      </div>
    `).join('');

    // Dynamic status cards updates based on timeline steps
    let hasHospital = false;
    let hospitalDetail = "Finding hospital...";
    let hospitalStatus = "";

    let hasAmbulance = false;
    let ambulanceDetail = "Dispatching ambulance...";
    let ambulanceStatus = "";

    let hasFamily = false;
    let familyDetail = "Notifying family...";
    let familyStatus = "";

    timeline.forEach(step => {
      const s = step.step ? step.step.toUpperCase() : '';
      if (s === 'HOSPITAL_MATCHED') {
        hasHospital = true;
        hospitalDetail = step.detail;
        hospitalStatus = step.status;
        _markDashboardStep('step-hospital', 'completed');
      }
      if (s === 'AMBULANCE_DISPATCHED' || s === 'AMBULANCE_CALL_STARTED') {
        hasAmbulance = true;
        ambulanceDetail = step.detail;
        ambulanceStatus = step.status === 'DISPATCHED' ? 'CALLING' : step.status;
        _markDashboardStep('step-ambulance', 'completed');
      }
      if (s === 'AMBULANCE_ACCEPTED') {
        hasAmbulance = true;
        ambulanceDetail = step.detail;
        ambulanceStatus = 'ACCEPTED';
        _markDashboardStep('step-ambulance', 'completed');
      }
      if (s === 'AMBULANCE_DECLINED') {
        hasAmbulance = true;
        ambulanceDetail = step.detail;
        ambulanceStatus = 'DECLINED';
      }
      if (s === 'FAMILY_NOTIFIED') {
        hasFamily = true;
        familyDetail = step.detail;
        familyStatus = step.status;
        _markDashboardStep('step-family', 'completed');
      }
      if (s === 'HOSPITAL_NOTIFIED') {
        _markDashboardStep('step-hospital-notified', 'completed');
      }
      if (s === 'EMERGENCY_COMPLETE' || s === 'REPORT_READY' || s === 'NOTIFICATIONS_SENT') {
        _markDashboardStep('step-report', 'completed');
      }
      if (s === 'HANDOVER_COMPLETED' || s === 'ARRIVED_AT_HOSPITAL') {
        _markDashboardStep('step-arrived', 'completed');
      }
    });

    const cardH = $('em-card-hospital');
    if (cardH && hasHospital) {
      setText('em-hospital-text', hospitalDetail);
      cardH.className = 'em-status-card ' + (hospitalStatus === 'SUCCESS' ? 'done' : hospitalStatus === 'FAILED' ? 'fail' : '');
    }

    const cardA = $('em-card-ambulance');
    if (cardA && hasAmbulance) {
      setText('em-ambulance-text', ambulanceDetail);
      cardA.className = 'em-status-card ' + (ambulanceStatus === 'ACCEPTED' ? 'done' : ambulanceStatus === 'CALLING' ? 'calling' : 'fail');
    }

    const cardF = $('em-card-family');
    if (cardF && hasFamily) {
      setText('em-family-text', familyDetail);
      cardF.className = 'em-status-card ' + (familyStatus === 'SENT' || familyStatus === 'DELIVERED' ? 'done' : familyStatus === 'SKIPPED' ? 'skipped' : 'fail');
    }
  }

  function _formatStep(step) {
    const map = {
      'EMERGENCY_ACTIVATED':   '🔴 Emergency Activated',
      'HOSPITAL_MATCHED':      '🏥 Hospital Discovery',
      'AMBULANCE_CALL_STARTED': '🚑 Ambulance Outbound Call',
      'AMBULANCE_ACCEPTED':    '✅ Ambulance Accepted',
      'AMBULANCE_DECLINED':    '❌ Ambulance Declined',
      'FAMILY_NOTIFIED':       '👪 Family Alert Dispatch',
      'HOSPITAL_NOTIFIED':     '🏥 Hospital Notification Alert',
      'consciousness_check':   '👁️ Consciousness Check',
      'escalated':             '⚠️ Emergency Escalated',
    };
    return map[step] || step.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
  }

  // ── Error Handling ───────────────────────────────────────────────────────
  function _handleTriggerError(errData, prediction) {
    // Fallback: still show overlay and use browser TTS
    setText('em-session-id', 'Emergency detected (offline mode)');
    _speakBrowserTTS(
      `Emergency detected: ${prediction.prediction}. Please stop your vehicle safely and call emergency services.`
    );
    console.error('[EmergencyMode] Trigger error:', errData);
  }

  function _defaultAlertText(prediction) {
    return `Hello. A possible ${prediction.prediction} has been detected. Please remain calm. Stop your vehicle safely. Emergency services are being contacted. Help is on the way.`;
  }

  // ── Dismiss ─────────────────────────────────────────────────────────────
  function dismiss() {
    const overlay = $('em-overlay');
    if (overlay) {
      overlay.style.animation = 'emergencyFadeIn 0.3s ease-out reverse';
      setTimeout(() => overlay.remove(), 300);
    }
    clearInterval(pollingInterval);
    clearInterval(consciousnessTimer);
    window.speechSynthesis?.cancel();
    isActive = false;
  }

  // ── Public API ───────────────────────────────────────────────────────────
  return {
    activate:        activateEmergency,
    respondConscious,
    respondNeedHelp,
    dismiss,
    getCurrentId:    () => currentEmergencyId,
    getSession:      () => sessionData,
    isEmergencyActive: () => isActive
  };

})();

// Expose globally so dashboard.js can call it
window.EmergencyMode = EmergencyMode;
