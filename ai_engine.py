import numpy as np
import pandas as pd
import os
import warnings
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

warnings.filterwarnings('ignore')

# Global variables for models
vitals_classifier = None
symptom_vectorizer = None
symptom_features = None

# Medical categories knowledge base for TF-IDF / Transformer similarity fallback
EMERGENCY_DESCRIPTIONS = {
    "Normal": "Vitals are within physiological limits. No acute stress or discomfort indicated.",
    "Mild Fever": "Elevated core body temperature and slightly elevated heart rate. Indicates mild infection or immune response.",
    "High Fever": "Significantly elevated body temperature, fast heart rate. High risk of dehydration and heat exhaustion.",
    "Fatigue": "High physical fatigue score, low sleep hours, lower blood pressure. Slowed reaction times.",
    "Sleep Deprivation": "Extremely low sleep hours, increased stress indicators, fatigue. Cognitive function impaired.",
    "Stress": "High stress score, elevated systolic and diastolic blood pressure, and heart rate. Chronic strain.",
    "Dehydration": "Low blood pressure, rapid heart rate, headache, dry mouth, dizziness. Inadequate fluid volume.",
    "Low Oxygen": "SpO2 below normal levels (Hypoxia). Shortness of breath, rapid breathing, cardiac strain.",
    "Arrhythmia": "Highly irregular, very high or very low heart rate. Palpitations, dizziness, chest discomfort.",
    "Heart Attack Risk": "Severe chest pain radiating to left arm, extreme hypertension or sudden crash, low SpO2, severe shortness of breath.",
    "Stroke Risk": "Critical hypertension (extremely high BP), numbness on one side, slurred speech, confusion, headache.",
    "Kidney Failure Risk": "Decreased urination, swollen ankles or legs, high blood pressure, extreme fatigue, drowsiness.",
    "Cardiac Arrest Risk": "Sudden heart rate spike/flatline, critical oxygen drop, loss of consciousness, gasping, zero pulse.",
    "Accident Risk": "Extreme drowsiness, micro-sleep, fatigue score critical, slow respiration, erratic heart rate."
}

# Explanation and Suggested Actions mapping
EMERGENCY_METADATA = {
    "Normal": {
        "severity": "Normal",
        "explanation": "All health parameters are within the standard safe operating limits. You are fit to drive.",
        "action": "Continue driving safely. Keep monitoring vitals."
    },
    "Mild Fever": {
        "severity": "Low",
        "explanation": "Body temperature is slightly elevated, suggesting a mild immune response or viral infection.",
        "action": "Please take rest. Drink sufficient water, monitor your temperature, and do not push yourself."
    },
    "High Fever": {
        "severity": "Moderate",
        "explanation": "Core temperature is above 38.3°C (101°F). High risk of heat exhaustion, dizziness, and decreased alertness.",
        "action": "Stop the vehicle at a safe spot, drink fluids, and seek medical attention to bring down the fever."
    },
    "Fatigue": {
        "severity": "Moderate",
        "explanation": "High fatigue scores and slightly reduced blood pressure suggest physical exhaustion. Driver reaction time is significantly impaired.",
        "action": "Pull over safely at a rest stop. Avoid long driving stretches and take a quick power nap."
    },
    "Sleep Deprivation": {
        "severity": "Moderate",
        "explanation": "Chronic sleep deficit (under 4 hours) combined with fatigue impairs spatial awareness and increases micro-sleep risk.",
        "action": "You are too tired to drive. Stop driving, drink coffee, or rest. Do not continue driving long distances."
    },
    "Stress": {
        "severity": "Low",
        "explanation": "High stress levels and slightly elevated blood pressure put strain on the cardiovascular system.",
        "action": "Practice slow breathing. Stop and take a short walk to calm down before continuing to drive."
    },
    "Dehydration": {
        "severity": "Moderate",
        "explanation": "Combination of low blood pressure and rapid heart rate points to significant fluid loss, leading to lightheadedness.",
        "action": "Stop driving immediately. Consume electrolytes/water. Wait for the dizziness to fade before driving."
    },
    "Low Oxygen": {
        "severity": "High",
        "explanation": "Oxygen saturation (SpO2) is dangerously low. Vital organs and the brain are not receiving sufficient oxygen.",
        "action": "Stop the vehicle immediately. Open the windows to let fresh air in. Seek medical oxygen support."
    },
    "Arrhythmia": {
        "severity": "High",
        "explanation": "Heart rate is highly irregular or extremely fast, showing signs of tachyarrhythmia or bradyarrhythmia.",
        "action": "Stop driving. Sit quietly. Avoid sudden movements. Emergency medical assessment is highly recommended."
    },
    "Heart Attack Risk": {
        "severity": "Critical",
        "explanation": "Severe chest pain, respiratory distress, and high blood pressure strongly indicate potential myocardial infarction (heart attack).",
        "action": "STOP driving immediately. Park the vehicle safely, activate hazard lights, sit still, and wait for emergency services. Do not exert yourself."
    },
    "Stroke Risk": {
        "severity": "Critical",
        "explanation": "Extremely high blood pressure combined with neurological symptoms (numbness, confusion) indicates potential acute stroke.",
        "action": "Stop driving immediately. Rest and stay calm. Emergency services are being requested. Time is critical."
    },
    "Kidney Failure Risk": {
        "severity": "High",
        "explanation": "Elevated blood pressure, systemic fatigue, and fluid retention symptoms suggest acute renal insufficiency.",
        "action": "Stop driving and contact your physician or visit the nearest emergency room for a blood and urine chemistry panel."
    },
    "Cardiac Arrest Risk": {
        "severity": "Critical",
        "explanation": "Vital signs show a complete collapse of circulation: extreme tachycardia, gasping respiration, and hypoxic oxygen saturation.",
        "action": "Critical emergency. Park the vehicle, call for emergency resuscitation support immediately. Do not attempt to drive."
    },
    "Accident Risk": {
        "severity": "High",
        "explanation": "Combination of severe fatigue, drowsiness, and sleep deprivation creates a critical risk of falling asleep at the wheel.",
        "action": "Stop driving immediately. Pull over to a safe area. Do not drive until you have had adequate sleep."
    }
}

# Try loading Hugging Face / Sentence Transformers only when explicitly enabled.
USE_SENTENCE_TRANSFORMERS = os.environ.get('USE_SENTENCE_TRANSFORMERS', '0') == '1'
HF_MODEL_NAME = 'all-MiniLM-L6-v2'
hf_model = None

if USE_SENTENCE_TRANSFORMERS:
    try:
        from sentence_transformers import SentenceTransformer, util
        print(f"Attempting to load Hugging Face Sentence-Transformer ('{HF_MODEL_NAME}')...")
        hf_model = SentenceTransformer(HF_MODEL_NAME)
        print("Hugging Face Sentence-Transformer loaded successfully.")
    except Exception as e:
        print(f"Hugging Face models not available or failed to load ({e}). Using Scikit-Learn TF-IDF for NLP similarity matching.")
else:
    print("Sentence-Transformers disabled by default. Set USE_SENTENCE_TRANSFORMERS=1 to enable it if your system supports Torch.")


def generate_synthetic_data(num_samples=1000):
    """Generates synthetic physiological data for training the classifier."""
    np.random.seed(42)
    data = []
    
    classes = list(EMERGENCY_METADATA.keys())
    
    for _ in range(num_samples):
        # Pick a random class
        label = np.random.choice(classes)
        
        # Default (normal) values
        hr = np.random.uniform(60, 90)
        spo2 = np.random.uniform(96, 100)
        temp = np.random.uniform(36.5, 37.2)
        sys_bp = np.random.uniform(110, 125)
        dia_bp = np.random.uniform(70, 85)
        resp = np.random.uniform(12, 18)
        sleep = np.random.uniform(7, 9)
        stress = np.random.uniform(1, 3)
        fatigue = np.random.uniform(1, 3)
        
        if label == "Mild Fever":
            temp = np.random.uniform(37.3, 38.2)
            hr = np.random.uniform(75, 95)
            fatigue = np.random.uniform(2, 5)
        elif label == "High Fever":
            temp = np.random.uniform(38.3, 40.5)
            hr = np.random.uniform(90, 115)
            resp = np.random.uniform(16, 22)
            fatigue = np.random.uniform(5, 8)
        elif label == "Fatigue":
            fatigue = np.random.uniform(6, 9)
            sleep = np.random.uniform(5, 6.5)
            sys_bp = np.random.uniform(95, 110)
            dia_bp = np.random.uniform(60, 75)
        elif label == "Sleep Deprivation":
            sleep = np.random.uniform(1, 4.5)
            fatigue = np.random.uniform(7, 10)
            stress = np.random.uniform(5, 8)
        elif label == "Stress":
            stress = np.random.uniform(7, 10)
            hr = np.random.uniform(80, 105)
            sys_bp = np.random.uniform(125, 145)
            dia_bp = np.random.uniform(80, 95)
        elif label == "Dehydration":
            hr = np.random.uniform(90, 115)
            sys_bp = np.random.uniform(85, 105)
            dia_bp = np.random.uniform(55, 70)
            fatigue = np.random.uniform(4, 7)
        elif label == "Low Oxygen":
            spo2 = np.random.uniform(80, 90)
            hr = np.random.uniform(90, 115)
            resp = np.random.uniform(20, 28)
        elif label == "Arrhythmia":
            # Irregular heart rates: very low (<55) or very high (>120)
            if np.random.rand() > 0.5:
                hr = np.random.uniform(120, 160)
            else:
                hr = np.random.uniform(40, 52)
            spo2 = np.random.uniform(91, 95)
        elif label == "Heart Attack Risk":
            hr = np.random.uniform(105, 140)
            spo2 = np.random.uniform(82, 92)
            sys_bp = np.random.uniform(150, 190)
            dia_bp = np.random.uniform(95, 120)
            resp = np.random.uniform(22, 30)
            stress = np.random.uniform(8, 10)
            fatigue = np.random.uniform(7, 10)
        elif label == "Stroke Risk":
            sys_bp = np.random.uniform(165, 210)
            dia_bp = np.random.uniform(100, 130)
            hr = np.random.uniform(80, 110)
            stress = np.random.uniform(7, 10)
        elif label == "Kidney Failure Risk":
            sys_bp = np.random.uniform(140, 175)
            dia_bp = np.random.uniform(90, 110)
            fatigue = np.random.uniform(7, 10)
            sleep = np.random.uniform(4, 7)
        elif label == "Cardiac Arrest Risk":
            hr = np.random.uniform(140, 190)
            spo2 = np.random.uniform(70, 84)
            sys_bp = np.random.uniform(160, 200)
            dia_bp = np.random.uniform(100, 120)
            resp = np.random.uniform(24, 34)
            stress = np.random.uniform(9, 10)
        elif label == "Accident Risk":
            sleep = np.random.uniform(1, 3)
            fatigue = np.random.uniform(8.5, 10)
            stress = np.random.uniform(8, 10)
            hr = np.random.uniform(85, 110)
            
        data.append([hr, spo2, temp, sys_bp, dia_bp, resp, sleep, stress, fatigue, label])
        
    df = pd.DataFrame(data, columns=[
        'heart_rate', 'spo2', 'temperature', 'systolic_bp', 'diastolic_bp', 
        'respiration_rate', 'sleep_hours', 'stress_level', 'fatigue_score', 'label'
    ])
    return df

def train_classifier():
    """Trains the Scikit-learn Random Forest classifier on vital parameters."""
    global vitals_classifier
    df = generate_synthetic_data(1200)
    X = df.drop('label', axis=1)
    y = df['label']
    
    # Train test split for validation metrics
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.15, random_state=42)
    
    clf = RandomForestClassifier(n_estimators=100, random_state=42, max_depth=12)
    clf.fit(X_train, y_train)
    
    train_acc = clf.score(X_train, y_train)
    test_acc = clf.score(X_test, y_test)
    print(f"Vitals classifier trained. Train Acc: {train_acc:.2%}, Test Acc: {test_acc:.2%}")
    vitals_classifier = clf

def train_nlp_fallback():
    """Trains a simple TF-IDF vectorizer on medical descriptions for similarity checks."""
    global symptom_vectorizer, symptom_features
    categories = list(EMERGENCY_DESCRIPTIONS.keys())
    descriptions = [EMERGENCY_DESCRIPTIONS[c] for c in categories]
    
    vectorizer = TfidfVectorizer(stop_words='english')
    symptom_features = vectorizer.fit_transform(descriptions)
    symptom_vectorizer = vectorizer
    print("NLP TF-IDF similarity model trained on clinical descriptions.")

def get_nlp_similarity(symptom_text):
    """Computes similarity of patient symptoms to medical conditions.
    Returns the closest matched emergency condition and confidence score."""
    if not symptom_text or symptom_text.strip() == "":
        return "Normal", 1.0

    categories = list(EMERGENCY_DESCRIPTIONS.keys())

    # Method 1: Hugging Face Sentence Transformers
    if hf_model is not None:
        try:
            symptom_embedding = hf_model.encode(symptom_text, convert_to_tensor=True)
            db_embeddings = hf_model.encode([EMERGENCY_DESCRIPTIONS[c] for c in categories], convert_to_tensor=True)
            
            from sentence_transformers import util
            cos_scores = util.cos_sim(symptom_embedding, db_embeddings)[0].tolist()
            
            best_idx = np.argmax(cos_scores)
            best_score = float(cos_scores[best_idx])
            matched_class = categories[best_idx]
            
            # Print similarity logic for validation
            print(f"HF Semantic Match: Input='{symptom_text}' matched to '{matched_class}' with similarity {best_score:.2f}")
            return matched_class, best_score
        except Exception as e:
            print(f"Error during Sentence-Transformer matching: {e}. Falling back to TF-IDF.")

    # Method 2: Scikit-learn TF-IDF Cosine Similarity (Fallback)
    if symptom_vectorizer is not None:
        query_vec = symptom_vectorizer.transform([symptom_text])
        similarities = cosine_similarity(query_vec, symptom_features)[0]
        best_idx = np.argmax(similarities)
        best_score = float(similarities[best_idx])
        
        # If similarity is too low, default to Normal unless vital rules flag it
        if best_score < 0.1:
            return "Normal", 0.0
            
        matched_class = categories[best_idx]
        print(f"TF-IDF Match: Input='{symptom_text}' matched to '{matched_class}' with similarity {best_score:.2f}")
        return matched_class, best_score

    return "Normal", 0.0

def predict_health_risk(vitals_dict):
    """Predicts risk class, severity, and generates clinical justifications.
    Inputs:
        vitals_dict: dict with keys:
            heart_rate, spo2, temperature, systolic_bp, diastolic_bp, 
            respiration_rate, sleep_hours, stress_level, fatigue_score, symptoms
    Outputs:
        dictionary with fields:
            prediction, confidence, risk_percentage, severity, explanation, suggested_action
    """
    # 1. Check database classifiers are loaded
    if vitals_classifier is None:
        train_classifier()
    if symptom_vectorizer is None:
        train_nlp_fallback()

    # Extract numeric features in proper order
    features = [
        float(vitals_dict.get('heart_rate', 75)),
        float(vitals_dict.get('spo2', 98)),
        float(vitals_dict.get('temperature', 36.8)),
        float(vitals_dict.get('systolic_bp', 120)),
        float(vitals_dict.get('diastolic_bp', 80)),
        float(vitals_dict.get('respiration_rate', 15)),
        float(vitals_dict.get('sleep_hours', 8)),
        float(vitals_dict.get('stress_level', 1)),
        float(vitals_dict.get('fatigue_score', 1))
    ]
    
    # Predict probabilities with the RF vital classifier
    feature_names = [
        'heart_rate', 'spo2', 'temperature', 'systolic_bp', 'diastolic_bp', 
        'respiration_rate', 'sleep_hours', 'stress_level', 'fatigue_score'
    ]
    features_df = pd.DataFrame([features], columns=feature_names)
    probs = vitals_classifier.predict_proba(features_df)[0]
    classes = vitals_classifier.classes_
    
    best_vital_idx = np.argmax(probs)
    vital_prediction = classes[best_vital_idx]
    vital_confidence = float(probs[best_vital_idx])
    
    # 2. Check NLP analysis for symptoms
    symptom_text = vitals_dict.get('symptoms', '')
    symptom_prediction, symptom_confidence = get_nlp_similarity(symptom_text)
    
    # 3. Decision Fusion Engine
    # If the ML model points to normal, but NLP symptoms explicitly match a high risk class, override.
    # Also, write rules for safety critical systems (Heart Attack, Stroke, Low Oxygen)
    final_prediction = vital_prediction
    final_confidence = vital_confidence
    
    spo2_val = features[1]
    hr_val = features[0]
    sys_bp = features[3]
    temp_val = features[2]
    
    # Hard clinical thresholds overrides (safety-first approach)
    if spo2_val < 85:
        final_prediction = "Cardiac Arrest Risk" if hr_val > 140 else "Low Oxygen"
        final_confidence = 0.95
    elif sys_bp >= 180 or (sys_bp >= 160 and "numbness" in symptom_text.lower()):
        final_prediction = "Stroke Risk"
        final_confidence = 0.92
    elif hr_val > 130 and "chest pain" in symptom_text.lower():
        final_prediction = "Heart Attack Risk"
        final_confidence = 0.96
    elif temp_val >= 39.0:
        final_prediction = "High Fever"
        final_confidence = 0.98
    elif symptom_prediction != "Normal" and symptom_confidence > 0.45:
        # Fuse models: if symptoms confirm a severe risk, elevate prediction
        meta_vital = EMERGENCY_METADATA[vital_prediction]["severity"]
        meta_symptom = EMERGENCY_METADATA[symptom_prediction]["severity"]
        
        # If symptoms show critical state, override ML predictions that might miss symptom signals
        if meta_symptom in ["Critical", "High"] and meta_vital not in ["Critical", "High"]:
            final_prediction = symptom_prediction
            final_confidence = (vital_confidence + symptom_confidence) / 2.0

    # Calculate Risk Percentage based on confidence and severity
    metadata = EMERGENCY_METADATA[final_prediction]
    severity = metadata["severity"]
    
    if severity == "Normal":
        risk_pct = max(5.0, final_confidence * 10)
    elif severity == "Low":
        risk_pct = 20.0 + (final_confidence * 20.0)
    elif severity == "Moderate":
        risk_pct = 40.0 + (final_confidence * 25.0)
    elif severity == "High":
        risk_pct = 65.0 + (final_confidence * 20.0)
    else:  # Critical
        risk_pct = 85.0 + (final_confidence * 14.0)
        
    risk_pct = min(100.0, float(risk_pct))
    
    # Return formatted results
    return {
        "prediction": final_prediction,
        "confidence": round(final_confidence, 2),
        "risk_percentage": round(risk_pct, 1),
        "severity": severity,
        "explanation": metadata["explanation"],
        "suggested_action": metadata["action"]
    }

def initialize_models():
    """Initialize AI models on first use or when the module is loaded explicitly."""
    if vitals_classifier is None:
        train_classifier()
    if symptom_vectorizer is None:
        train_nlp_fallback()

if __name__ == '__main__':
    initialize_models()
    # Test a normal case
    test_normal = {
        'heart_rate': 72, 'spo2': 98, 'temperature': 36.7, 'systolic_bp': 120, 'diastolic_bp': 80,
        'respiration_rate': 14, 'sleep_hours': 8, 'stress_level': 2, 'fatigue_score': 2, 'symptoms': ''
    }
    # Test an emergency cardiac case
    test_cardiac = {
        'heart_rate': 135, 'spo2': 84, 'temperature': 36.8, 'systolic_bp': 175, 'diastolic_bp': 105,
        'respiration_rate': 26, 'sleep_hours': 4, 'stress_level': 9, 'fatigue_score': 8, 'symptoms': 'severe chest pain, breathing difficulties'
    }
    
    print("\n--- Testing AI Engine predictions ---")
    print("Normal Case Vitals:", predict_health_risk(test_normal))
    print("Cardiac Case Vitals:", predict_health_risk(test_cardiac))
