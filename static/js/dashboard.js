/**
 * AI Driver Health Guardian - Driver Dashboard Controller
 */

let vitalsChart;
const driverLocation = { 
    lat: (window.driverInitialLat && !isNaN(window.driverInitialLat)) ? parseFloat(window.driverInitialLat) : 11.3410, 
    lng: (window.driverInitialLng && !isNaN(window.driverInitialLng)) ? parseFloat(window.driverInitialLng) : 77.7170 
};

document.addEventListener("DOMContentLoaded", function() {
    // 1. Initialize Leaflet Map and auto-load logistics dispatch route
    if (document.getElementById('map')) {
        try {
            NavigationSystem.initMap(driverLocation.lat, driverLocation.lng);
            NavigationSystem.findNearestHospital(driverLocation.lat, driverLocation.lng, 'General Emergency', null);
        } catch (e) {
            console.error("Map initialization failed:", e);
        }
    }

    // 2. Initialize Charts
    initVitalsChart();

    // 3. Form Submission
    const form = document.getElementById('vitals-form');
    if (form) {
        form.addEventListener('submit', function(e) {
            e.preventDefault();
            submitVitals();
        });
    }

    // 4. Voice Command Recognition button
    const dictationBtn = document.getElementById('voice-dictation-btn');
    if (dictationBtn) {
        dictationBtn.addEventListener('click', function() {
            startVoiceInput();
        });
    }
});

// Initialize historical Chart.js graphs
function initVitalsChart() {
    const ctx = document.getElementById('vitalsTrendChart');
    if (!ctx) return;

    // Build charts with mock trend lines initially
    vitalsChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: ['12:00', '12:10', '12:20', '12:30', '12:40', '12:50', '13:00'],
            datasets: [
                {
                    label: 'Heart Rate (bpm)',
                    data: [72, 75, 71, 74, 80, 78, 75],
                    borderColor: '#00e5ff',
                    backgroundColor: 'rgba(0, 229, 255, 0.05)',
                    borderWidth: 2.5,
                    tension: 0.35,
                    yAxisID: 'y'
                },
                {
                    label: 'SpO₂ (%)',
                    data: [98, 98, 99, 97, 98, 98, 98],
                    borderColor: '#10b981',
                    backgroundColor: 'rgba(16, 185, 129, 0.05)',
                    borderWidth: 2.5,
                    tension: 0.35,
                    yAxisID: 'y1'
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    labels: { color: '#94a3b8', font: { family: 'Outfit' } }
                }
            },
            scales: {
                x: {
                    grid: { color: 'rgba(255, 255, 255, 0.05)' },
                    ticks: { color: '#94a3b8', font: { family: 'Outfit' } }
                },
                y: {
                    type: 'linear',
                    display: true,
                    position: 'left',
                    grid: { color: 'rgba(255, 255, 255, 0.05)' },
                    ticks: { color: '#94a3b8' }
                },
                y1: {
                    type: 'linear',
                    display: true,
                    position: 'right',
                    grid: { drawOnChartArea: false },
                    ticks: { color: '#94a3b8' }
                }
            }
        }
    });
}

// Submit vitals to AI model endpoint
function submitVitals() {
    // Update global driverLocation coordinates
    const latInput = document.getElementById('input-lat');
    const lngInput = document.getElementById('input-lng');
    if (latInput && lngInput) {
        driverLocation.lat = parseFloat(latInput.value);
        driverLocation.lng = parseFloat(lngInput.value);
    }

    // Get form inputs
    const vitals = {
        heart_rate: parseFloat(document.getElementById('input-hr').value),
        spo2: parseFloat(document.getElementById('input-spo2').value),
        temperature: parseFloat(document.getElementById('input-temp').value),
        systolic_bp: parseFloat(document.getElementById('input-sysbp').value),
        diastolic_bp: parseFloat(document.getElementById('input-diabp').value),
        respiration_rate: parseFloat(document.getElementById('input-resp').value),
        sleep_hours: parseFloat(document.getElementById('input-sleep').value),
        stress_level: parseFloat(document.getElementById('input-stress').value),
        fatigue_score: parseFloat(document.getElementById('input-fatigue').value),
        symptoms: document.getElementById('input-symptoms').value,
        lat: (typeof driverLocation !== 'undefined' && driverLocation.lat) ? driverLocation.lat : 11.3410,
        lng: (typeof driverLocation !== 'undefined' && driverLocation.lng) ? driverLocation.lng : 77.7170
    };

    // Update frontend gauges immediately
    updateGauges(vitals);

    // Call Vitals Analysis API
    fetch('/api/vitals', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(vitals)
    })
    .then(response => response.json())
    .then(data => {
        if (data.error) {
            MainApp.showNotification("Data Error", data.error, "danger");
            return;
        }

        const prediction = data.prediction;
        const emergencyId = data.emergency_id;

        // Render AI Results Panel
        document.getElementById('result-class').innerText = prediction.prediction;
        document.getElementById('result-severity').innerText = prediction.severity;
        document.getElementById('result-confidence').innerText = (prediction.confidence * 100) + "%";
        document.getElementById('result-explanation').innerText = prediction.explanation;
        document.getElementById('result-action').innerText = prediction.suggested_action;
        
        // Style severity text
        const severityBadge = document.getElementById('result-severity');
        severityBadge.className = 'badge';
        if (prediction.severity === 'Normal' && !emergencyId) {
            severityBadge.classList.add('bg-success');
            resetEmergencyUI();
            VoiceAssistant.speak(prediction.explanation);
        } else {
            // Activate Emergency Workflow for Moderate, High, Critical or Active Emergency ID
            const badgeClass = prediction.severity === 'Moderate' ? 'bg-warning' : (prediction.severity === 'Low' ? 'bg-info' : 'bg-danger');
            severityBadge.classList.add(badgeClass);
            triggerEmergencySequence(prediction, emergencyId, vitals);

            if (window.EmergencyMode && !EmergencyMode.isEmergencyActive()) {
                setTimeout(() => {
                    const lat = (typeof driverLocation !== 'undefined' && driverLocation.lat) ? driverLocation.lat : 11.3410;
                    const lng = (typeof driverLocation !== 'undefined' && driverLocation.lng) ? driverLocation.lng : 77.7170;
                    EmergencyMode.activate(
                        prediction,
                        vitals,
                        lat,
                        lng
                    );
                }, 300);
            }
        }



        // Add dynamic vital to Chart
        updateChartData(vitals.heart_rate, vitals.spo2);
        
        MainApp.showNotification("AI Analysis Complete", `Classified as ${prediction.prediction}`, prediction.severity === 'Critical' ? 'danger' : 'info');
    })
    .catch(err => console.error("Error submitting vitals:", err));
}

// Update charts with new vitals
function updateChartData(hr, spo2) {
    if (!vitalsChart) return;
    
    const now = new Date();
    const timeLabel = now.getHours() + ":" + String(now.getMinutes()).padStart(2, '0');
    
    vitalsChart.data.labels.push(timeLabel);
    vitalsChart.data.datasets[0].data.push(hr);
    vitalsChart.data.datasets[1].data.push(spo2);
    
    // Maintain maximum 10 points
    if (vitalsChart.data.labels.length > 10) {
        vitalsChart.data.labels.shift();
        vitalsChart.data.datasets[0].data.shift();
        vitalsChart.data.datasets[1].data.shift();
    }
    
    vitalsChart.update();
}

// Update interactive gauges
function updateGauges(vitals) {
    document.getElementById('gauge-hr').innerText = vitals.heart_rate;
    document.getElementById('gauge-spo2').innerText = vitals.spo2 + "%";
    document.getElementById('gauge-temp').innerText = vitals.temperature + "°C";
    document.getElementById('gauge-bp').innerText = vitals.systolic_bp + "/" + vitals.diastolic_bp;
    
    // Stress and Fatigue indicators
    document.getElementById('gauge-stress').style.width = (vitals.stress_level * 10) + "%";
    document.getElementById('gauge-fatigue').style.width = (vitals.fatigue_score * 10) + "%";
}

// Trigger emergency chain reaction backed by database events
function triggerEmergencySequence(prediction, emergencyId, vitals) {
    const overlay = document.getElementById('critical-overlay');
    if (overlay) overlay.style.display = 'block';

    resetTimeline();
    setTimelineStep('step-vitals', 'completed');
    setTimelineStep('step-prediction', 'completed');
    
    // Voice Assistant message
    const driverName = document.getElementById('driver-name-holder')?.innerText || "Driver";
    const voiceMessage = `Warning. Alert detected. Hello ${driverName}. A possible ${prediction.prediction} hazard has been diagnosed. Please pull over and stop your vehicle safely. Emergency services are being dispatched.`;
    
    VoiceAssistant.speak(voiceMessage);
    setTimelineStep('step-voice', 'completed');

    if (emergencyId) {
        pollBackendEmergencyTimeline(emergencyId);
    } else {
        // Fallback query nearest hospital
        NavigationSystem.findNearestHospital(driverLocation.lat, driverLocation.lng, prediction.prediction, null, function(data) {
            setTimelineStep('step-hospital', 'completed');
            setTimelineStep('step-ambulance', 'completed');
        });
    }
}

function pollBackendEmergencyTimeline(emergencyId) {
    let attempts = 0;
    const interval = setInterval(() => {
        attempts++;
        fetch(`/api/emergency/${emergencyId}/timeline`)
            .then(r => r.json())
            .then(data => {
                if (!data.success || !data.timeline) return;

                const stepsCompleted = new Set(data.timeline.map(t => t.step));
                if (stepsCompleted.has('EMERGENCY_ACTIVATED') || stepsCompleted.has('vitals_logged')) {
                    setTimelineStep('step-vitals', 'completed');
                    setTimelineStep('step-prediction', 'completed');
                }
                if (stepsCompleted.has('HOSPITAL_MATCHED')) {
                    setTimelineStep('step-hospital', 'completed');
                }
                if (stepsCompleted.has('AMBULANCE_DISPATCHED') || stepsCompleted.has('ambulance_accepted')) {
                    setTimelineStep('step-ambulance', 'completed');
                }
                if (stepsCompleted.has('notifications_sent') || stepsCompleted.has('hospital_alerted')) {
                    setTimelineStep('step-family', 'completed');
                    setTimelineStep('step-hospital-notified', 'completed');
                }
                if (stepsCompleted.has('DOCTOR_CONSULTATION') || stepsCompleted.has('report_created')) {
                    setTimelineStep('step-report', 'completed');
                }

                if (attempts >= 10 || stepsCompleted.has('DOCTOR_CONSULTATION')) {
                    clearInterval(interval);
                }
            })
            .catch(e => console.log('Timeline poll notice:', e));
    }, 2000);
}

function resetEmergencyUI() {
    const overlay = document.getElementById('critical-overlay');
    if (overlay) overlay.style.display = 'none';
    
    const banner = document.getElementById('emergency-banner');
    if (banner) banner.style.display = 'none';
    
    const dlBtn = document.getElementById('download-report-btn');
    if (dlBtn) dlBtn.style.display = 'none';
}

// Timeline state handlers
function resetTimeline() {
    const steps = ['step-vitals', 'step-prediction', 'step-voice', 'step-hospital', 'step-ambulance', 'step-family', 'step-hospital-notified', 'step-report', 'step-arrived'];
    steps.forEach(step => {
        const el = document.getElementById(step);
        if (el) el.className = 'timeline-step';
    });
}

function setTimelineStep(id, state) {
    const el = document.getElementById(id);
    if (el) {
        el.className = 'timeline-step ' + state;
    }
}

// Voice Recognition Dictation Vitals Entry Helper
function startVoiceInput() {
    const statusTxt = document.getElementById('voice-status-text');
    statusTxt.innerText = "Listening for clinical dictation...";
    
    VoiceAssistant.startListening(
        // Result callback
        function(transcript) {
            statusTxt.innerText = `Recognized: "${transcript}"`;
            parseVitalsVoiceInput(transcript);
        },
        // Error callback
        function(error) {
            statusTxt.innerText = `Error: ${error}`;
            MainApp.showNotification("Voice Input", "Failed to recognize speech. Please speak clearly.", "warning");
        },
        // Start callback
        function() {
            statusTxt.innerText = "Listening...";
        },
        // End callback
        function() {
            setTimeout(() => { statusTxt.innerText = ""; }, 3000);
        }
    );
}

// Parse spoken parameters: e.g. "Heart rate 120 and oxygen 88 chest pain"
function parseVitalsVoiceInput(text) {
    const lower = text.toLowerCase();
    
    // Extract heart rate
    const hrMatch = lower.match(/(heart rate|pulse)\s*(is|of)?\s*(\d+)/);
    if (hrMatch) document.getElementById('input-hr').value = hrMatch[3];
    
    // Extract oxygen
    const oxygenMatch = lower.match(/(oxygen|oxygen level|spo2)\s*(is|of)?\s*(\d+)/);
    if (oxygenMatch) document.getElementById('input-spo2').value = oxygenMatch[3];

    // Extract temperature
    const tempMatch = lower.match(/(temp|temperature)\s*(is|of)?\s*(\d+(\.\d+)?)/);
    if (tempMatch) document.getElementById('input-temp').value = tempMatch[3];

    // Extract symptoms
    const symptomKeywords = ["chest pain", "pain", "numbness", "breathing difficulty", "cough", "slurred speech", "dizzy", "headache"];
    let detectedSymptoms = [];
    symptomKeywords.forEach(keyword => {
        if (lower.includes(keyword)) {
            detectedSymptoms.push(keyword);
        }
    });
    if (detectedSymptoms.length > 0) {
        document.getElementById('input-symptoms').value = detectedSymptoms.join(", ");
    }
    
    MainApp.showNotification("Voice Input Dictation", "Extracted physiological values from speech.", "success");
}
