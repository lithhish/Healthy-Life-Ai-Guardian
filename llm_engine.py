"""
AI Driver Health Guardian — LLM Reasoning Engine

Tries: Ollama (local Llama3/Gemma/Mistral) → Hugging Face pipeline → Template fallback
Set USE_OLLAMA=1 and OLLAMA_MODEL=llama3 to enable local LLM.
"""

import os
import json
import requests

OLLAMA_URL = os.environ.get('OLLAMA_URL', 'http://127.0.0.1:11434')
OLLAMA_MODEL = os.environ.get('OLLAMA_MODEL', 'llama3')
USE_OLLAMA = os.environ.get('USE_OLLAMA', '0') == '1'

# ──────────────────────────────────────────────────
# Medical department routing
# ──────────────────────────────────────────────────
DEPARTMENT_MAP = {
    'Heart Attack Risk':   {'dept': 'Cardiology',          'specialty': 'Cardiac',    'color': '#ef4444'},
    'Cardiac Arrest Risk': {'dept': 'Cardiology / ICU',    'specialty': 'Cardiac',    'color': '#dc2626'},
    'Arrhythmia':          {'dept': 'Cardiology',          'specialty': 'Cardiac',    'color': '#f97316'},
    'Stroke Risk':         {'dept': 'Neurology',           'specialty': 'Neurology',  'color': '#a855f7'},
    'Kidney Failure Risk': {'dept': 'Nephrology',          'specialty': 'Kidney',     'color': '#3b82f6'},
    'Low Oxygen':          {'dept': 'Pulmonology / ICU',   'specialty': 'ICU',        'color': '#06b6d4'},
    'High Fever':          {'dept': 'General Medicine',    'specialty': 'ICU',        'color': '#eab308'},
    'Dehydration':         {'dept': 'Emergency Medicine',  'specialty': 'ICU',        'color': '#84cc16'},
    'Fatigue':             {'dept': 'General Medicine',    'specialty': 'General',    'color': '#94a3b8'},
    'Sleep Deprivation':   {'dept': 'Neurology',           'specialty': 'General',    'color': '#64748b'},
    'Stress':              {'dept': 'Psychiatry',          'specialty': 'General',    'color': '#8b5cf6'},
    'Accident Risk':       {'dept': 'Trauma / Emergency',  'specialty': 'Trauma',     'color': '#f59e0b'},
    'Mild Fever':          {'dept': 'General Medicine',    'specialty': 'General',    'color': '#22c55e'},
    'Normal':              {'dept': 'No Action Required',  'specialty': 'General',    'color': '#10b981'},
}

LIFE_THREATENING = {
    'Heart Attack Risk', 'Cardiac Arrest Risk', 'Stroke Risk',
    'Kidney Failure Risk', 'Low Oxygen', 'Accident Risk'
}

CRITICAL_SEVERITIES = {'Critical', 'High'}


def classify_required_department(emergency_type: str) -> dict:
    """Return department and specialty for a given emergency classification."""
    return DEPARTMENT_MAP.get(emergency_type, DEPARTMENT_MAP['Normal'])


def is_life_threatening(prediction_result: dict) -> bool:
    """Return True if the prediction warrants auto-emergency mode activation."""
    pred = prediction_result.get('prediction', 'Normal')
    sev  = prediction_result.get('severity', 'Normal')
    conf = prediction_result.get('confidence', 0.0)

    if pred in LIFE_THREATENING and conf >= 0.70:
        return True
    if sev == 'Critical':
        return True
    if sev == 'High' and conf >= 0.80:
        return True
    return False


# ──────────────────────────────────────────────────
# Template-based reasoning (always available fallback)
# ──────────────────────────────────────────────────
REASONING_TEMPLATES = {
    'Heart Attack Risk': (
        "The patient's vitals show a dangerous combination of elevated heart rate ({hr} bpm), "
        "reduced oxygen saturation ({spo2}%), elevated blood pressure ({sys_bp}/{dia_bp} mmHg), "
        "and increased respiration rate ({resp} rpm). These parameters, combined with the reported "
        "symptoms, are consistent with an acute myocardial infarction (heart attack) pattern. "
        "Immediate cardiac intervention is required. The patient should not drive and must be "
        "transported to a cardiac-capable facility without delay."
    ),
    'Cardiac Arrest Risk': (
        "Critical vital sign collapse detected: heart rate of {hr} bpm, SpO2 of {spo2}%, "
        "blood pressure {sys_bp}/{dia_bp} mmHg, and respiration rate {resp} rpm. "
        "This pattern indicates a life-threatening cardiovascular failure consistent with "
        "impending or ongoing cardiac arrest. Immediate CPR-capable emergency response and "
        "AED availability are required. Patient consciousness is at immediate risk."
    ),
    'Stroke Risk': (
        "Severely elevated systolic blood pressure of {sys_bp} mmHg with diastolic {dia_bp} mmHg "
        "indicates hypertensive crisis. Combined with neurological symptoms and stress indicators, "
        "this pattern is consistent with an acute cerebrovascular accident (stroke). "
        "Every minute of delayed treatment increases irreversible brain damage. "
        "Immediate neurology department intervention is critical."
    ),
    'Low Oxygen': (
        "Oxygen saturation at {spo2}% represents dangerous hypoxia. Normal SpO2 should be "
        "above 95%. At this level, vital organs including the brain are deprived of adequate "
        "oxygen. With heart rate at {hr} bpm and respiration at {resp} rpm, respiratory "
        "failure is a serious risk. Supplemental oxygen and immediate medical evaluation required."
    ),
    'Kidney Failure Risk': (
        "The combination of elevated blood pressure ({sys_bp}/{dia_bp} mmHg), high fatigue, "
        "and the overall vital pattern suggests acute renal insufficiency. Kidney failure "
        "leads to toxin accumulation in the bloodstream. The patient requires immediate "
        "nephrological evaluation and blood chemistry analysis."
    ),
    'Arrhythmia': (
        "Heart rate of {hr} bpm is significantly outside the normal range (60–100 bpm), "
        "indicating possible tachyarrhythmia or bradyarrhythmia. Irregular heart rhythm "
        "reduces cardiac output and can precipitate sudden cardiac events. "
        "Immediate cardiac monitoring and evaluation is recommended."
    ),
    'High Fever': (
        "Body temperature of {temp}°C exceeds the fever threshold of 38.3°C significantly. "
        "High fever with heart rate {hr} bpm and increased respiration indicates systemic "
        "infection or heat stroke. Prolonged high fever can cause organ damage. "
        "Medical attention and fever reduction measures are urgent."
    ),
    'Accident Risk': (
        "Extreme fatigue score combined with minimal sleep hours creates a critical "
        "microsleep risk. The patient should immediately stop driving. "
        "With heart rate at {hr} bpm and stress level elevated, cognitive impairment "
        "is severe. Continuing to drive risks a fatal accident."
    ),
}

_DEFAULT_REASONING = (
    "AI analysis of the patient's current vital signs indicates a {prediction} condition "
    "with {confidence}% confidence. Severity classification: {severity}. "
    "Current readings: Heart Rate {hr} bpm, SpO2 {spo2}%, Blood Pressure {sys_bp}/{dia_bp} mmHg, "
    "Temperature {temp}°C, Respiration {resp} rpm. "
    "The patient requires medical evaluation based on these findings."
)


def _template_reasoning(vitals: dict, prediction_result: dict) -> str:
    """Generate clinical reasoning from templates (no LLM required)."""
    pred = prediction_result.get('prediction', 'Normal')
    template = REASONING_TEMPLATES.get(pred, _DEFAULT_REASONING)

    hr = vitals.get('heart_rate', '--')
    spo2 = vitals.get('spo2', '--')
    temp = vitals.get('temperature', '--')
    sys_bp = vitals.get('systolic_bp', '--')
    dia_bp = vitals.get('diastolic_bp', '--')
    resp = vitals.get('respiration_rate', '--')

    return template.format(
        hr=hr, spo2=spo2, temp=temp,
        sys_bp=sys_bp, dia_bp=dia_bp, resp=resp,
        prediction=pred,
        confidence=round(float(prediction_result.get('confidence', 0)) * 100, 1),
        severity=prediction_result.get('severity', 'Unknown')
    )


# ──────────────────────────────────────────────────
# Ollama LLM (optional — Llama3/Gemma/Mistral)
# ──────────────────────────────────────────────────
def _ollama_reasoning(vitals: dict, prediction_result: dict) -> str:
    """Query local Ollama LLM for clinical reasoning."""
    pred = prediction_result.get('prediction', 'Normal')
    sev = prediction_result.get('severity', 'Unknown')
    conf = round(float(prediction_result.get('confidence', 0)) * 100, 1)

    prompt = f"""You are a medical AI assistant in an emergency vehicle health monitoring system.
A patient has been classified as: {pred} (Severity: {sev}, Confidence: {conf}%)

Patient vital signs:
- Heart Rate: {vitals.get('heart_rate')} bpm
- SpO2: {vitals.get('spo2')}%
- Blood Pressure: {vitals.get('systolic_bp')}/{vitals.get('diastolic_bp')} mmHg
- Temperature: {vitals.get('temperature')}°C
- Respiration Rate: {vitals.get('respiration_rate')} rpm
- Stress Level: {vitals.get('stress_level')}/10
- Fatigue Score: {vitals.get('fatigue_score')}/10
- Reported Symptoms: {vitals.get('symptoms', 'None')}

In 3-4 sentences, provide a clear clinical explanation of why these vitals indicate {pred},
what organ systems are at risk, and why immediate medical intervention is required.
Be concise, professional, and suitable for emergency medical documentation.
Do not include disclaimers or markdown formatting."""

    try:
        payload = {
            "model": OLLAMA_MODEL,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.2, "num_predict": 200}
        }
        response = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json=payload,
            timeout=8
        )
        if response.status_code == 200:
            result = response.json()
            return result.get('response', '').strip()
    except Exception as e:
        print(f"[LLMEngine] Ollama error: {e}")

    return None


# ──────────────────────────────────────────────────
# Public interface
# ──────────────────────────────────────────────────
def generate_llm_reasoning(vitals: dict, prediction_result: dict) -> str:
    """
    Generate clinical reasoning text.
    Tries Ollama if USE_OLLAMA=1, else uses template fallback.
    """
    if USE_OLLAMA:
        result = _ollama_reasoning(vitals, prediction_result)
        if result:
            return result

    return _template_reasoning(vitals, prediction_result)


def generate_emergency_action_plan(emergency_type: str, driver_name: str) -> list:
    """Return ordered list of emergency action steps."""
    base_steps = [
        f"Activate hazard lights on vehicle immediately",
        f"Stop the vehicle safely at the nearest safe location",
        f"Do not attempt to drive further",
        f"Unlock vehicle doors to allow emergency access",
        f"Stay seated and breathe slowly and deeply",
        f"Wait for emergency services — ambulance is dispatched",
    ]

    type_specific = {
        'Heart Attack Risk': [
            "Chew one aspirin (325mg) if available and not allergic",
            "Loosen any tight clothing around chest and neck",
            "Do not eat or drink anything",
        ],
        'Cardiac Arrest Risk': [
            "If anyone is nearby, call for help immediately",
            "AED (defibrillator) use may be required",
            "CPR may be needed if consciousness is lost",
        ],
        'Stroke Risk': [
            "Do not give any food, drink, or medication",
            "Keep the patient lying down with head slightly elevated",
            "Note the exact time symptoms started — critical for treatment",
        ],
        'Low Oxygen': [
            "Open all vehicle windows immediately for fresh air",
            "Sit upright to maximize lung capacity",
            "Breathe slowly and deeply through your nose",
        ],
    }

    steps = base_steps.copy()
    if emergency_type in type_specific:
        steps.extend(type_specific[emergency_type])

    return steps
