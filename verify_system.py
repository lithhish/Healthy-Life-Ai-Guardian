import os
import unittest

from database import (
    init_db,
    get_db_connection,
    generate_unique_driver_id,
    generate_unique_hospital_id,
    generate_unique_family_id,
    generate_unique_ambulance_id,
    generate_unique_staff_id,
)

from ai_engine import predict_health_risk
from hospital_recommender import haversine_distance
from geocoding_service import geocode_address
from hospital_recommender import (
    rank_hospitals_for_emergency,
    get_best_hospital_for_emergency,
)
import otp_service
from report_generator import generate_medical_report


class TestAiDriverHealthGuardian(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # Initialize SQLite database
        init_db()

    def test_database_seeding_and_auto_ids(self):
        conn = get_db_connection()
        cursor = conn.cursor()

        # Verify users exist
        cursor.execute("SELECT COUNT(*) FROM users")
        user_count = cursor.fetchone()[0]

        self.assertGreaterEqual(
            user_count,
            3,
            "Database should seed at least 3 users."
        )

        # Verify hospitals exist
        cursor.execute("SELECT COUNT(*) FROM hospitals")
        hosp_count = cursor.fetchone()[0]

        self.assertGreaterEqual(
            hosp_count,
            5,
            "Database should seed at least 5 hospitals."
        )

        # Verify ambulances exist
        cursor.execute("SELECT COUNT(*) FROM ambulances")
        amb_count = cursor.fetchone()[0]

        self.assertGreaterEqual(
            amb_count,
            5,
            "Database should seed at least 5 ambulances."
        )

        # Verify auto-generated unique ID formats
        drv_id = generate_unique_driver_id(conn)
        hos_id = generate_unique_hospital_id(conn)
        fam_id = generate_unique_family_id(conn)
        amb_id = generate_unique_ambulance_id(conn)
        doc_id = generate_unique_staff_id("doctor", conn)
        nur_id = generate_unique_staff_id("nurse", conn)

        self.assertTrue(
            drv_id.startswith("DRV-"),
            f"Driver ID should start with DRV-: {drv_id}"
        )

        self.assertTrue(
            hos_id.startswith("HOS-"),
            f"Hospital ID should start with HOS-: {hos_id}"
        )

        self.assertTrue(
            fam_id.startswith("FAM-"),
            f"Family ID should start with FAM-: {fam_id}"
        )

        self.assertTrue(
            amb_id.startswith("AMB-"),
            f"Ambulance ID should start with AMB-: {amb_id}"
        )

        self.assertTrue(
            doc_id.startswith("DOC-"),
            f"Doctor ID should start with DOC-: {doc_id}"
        )

        self.assertTrue(
            nur_id.startswith("NUR-"),
            f"Nurse ID should start with NUR-: {nur_id}"
        )

        conn.close()

    def test_ai_classifier_normal(self):
        vitals = {
            "heart_rate": 72.0,
            "spo2": 98.0,
            "temperature": 36.8,
            "systolic_bp": 120.0,
            "diastolic_bp": 80.0,
            "respiration_rate": 14.0,
            "sleep_hours": 8.0,
            "stress_level": 2.0,
            "fatigue_score": 2.0,
            "symptoms": "",
        }

        res = predict_health_risk(vitals)

        self.assertEqual(res["prediction"], "Normal")
        self.assertEqual(res["severity"], "Normal")
        self.assertLessEqual(res["risk_percentage"], 10.0)

    def test_ai_classifier_hypoxia_override(self):
        vitals = {
            "heart_rate": 85.0,
            "spo2": 83.0,
            "temperature": 36.8,
            "systolic_bp": 120.0,
            "diastolic_bp": 80.0,
            "respiration_rate": 24.0,
            "sleep_hours": 8.0,
            "stress_level": 5.0,
            "fatigue_score": 4.0,
            "symptoms": "shortness of breath",
        }

        res = predict_health_risk(vitals)

        self.assertEqual(res["prediction"], "Low Oxygen")
        self.assertEqual(res["severity"], "High")
        self.assertGreaterEqual(res["risk_percentage"], 65.0)

    def test_ai_classifier_cardiac_arrest_override(self):
        vitals = {
            "heart_rate": 145.0,
            "spo2": 82.0,
            "temperature": 36.8,
            "systolic_bp": 175.0,
            "diastolic_bp": 105.0,
            "respiration_rate": 28.0,
            "sleep_hours": 4.0,
            "stress_level": 9.0,
            "fatigue_score": 9.0,
            "symptoms": "severe chest pain, numbness, left arm tightness",
        }

        res = predict_health_risk(vitals)

        self.assertEqual(
            res["prediction"],
            "Cardiac Arrest Risk"
        )

        self.assertEqual(
            res["severity"],
            "Critical"
        )

        self.assertGreaterEqual(
            res["risk_percentage"],
            85.0
        )

    def test_haversine_distance(self):
        # Perundurai to Lotus Hospital Erode
        dist = haversine_distance(
            11.2720,
            77.5920,
            11.3410,
            77.7170
        )

        self.assertAlmostEqual(
            dist,
            15.65,
            delta=1.5
        )

    def test_geocoding_service(self):
        lat, lng = geocode_address(
            "Perundurai, Tamil Nadu, India"
        )

        self.assertIsInstance(lat, float)
        self.assertIsInstance(lng, float)
        self.assertGreater(lat, 0.0)

    def test_hospital_recommender(self):
        ranked = rank_hospitals_for_emergency(
            11.2720,
            77.5920,
            "Heart Attack Risk",
            "Cardiac"
        )

        self.assertGreater(
            len(ranked),
            0
        )

        best = ranked[0]

        self.assertIn(
            "score",
            best
        )

        self.assertIn(
            "distance_km",
            best
        )

        self.assertGreater(
            best["score"],
            0
        )

    def test_otp_service(self):
        test_phone = "+919876543210"

        res_send = otp_service.send_otp(
            test_phone,
            "test_verification"
        )

        self.assertTrue(
            res_send["success"]
        )

        otp_code = res_send["otp_code"]

        self.assertEqual(
            len(otp_code),
            6
        )

        # Verify correct OTP
        res_verify = otp_service.verify_otp(
            test_phone,
            otp_code,
            "test_verification"
        )

        self.assertTrue(
            res_verify["success"]
        )

    def test_pdf_report_generation(self):
        driver = {
            "name": "Test Driver",
            "age": 30,
            "gender": "Male",
            "blood_group": "O+",
            "height": 175,
            "weight": 70,
            "vehicle_number": "TN-33-1234",
            "driving_license": "DL1234",
            "emergency_contacts": "None",
            "insurance": "None",
            "address": "Perundurai",
            "family_details": "None",
        }

        health = {
            "heart_rate": 140,
            "spo2": 85,
            "temperature": 37.0,
            "systolic_bp": 160,
            "diastolic_bp": 100,
            "respiration_rate": 24,
            "sleep_hours": 6,
            "stress_level": 8,
            "fatigue_score": 8,
            "symptoms": "Chest tightness",
        }

        prediction = {
            "prediction": "Heart Attack Risk",
            "confidence": 0.95,
            "risk_percentage": 95.0,
            "severity": "Critical",
            "explanation": "Test explanation",
            "suggested_action": "Test action",
        }

        hospital = {
            "name": "Test Hospital",
            "emergency_number": "108",
            "address": "Main St",
            "emergency_types": "Cardiac, ICU",
            "latitude": 11.27,
            "longitude": 77.59,
        }

        ambulance = {
            "vehicle_number": "AMB-100",
            "driver_name": "Driver A",
            "driver_phone": "9999999999",
            "eta_minutes": 5,
        }

        output_pdf = os.path.join(
            os.path.dirname(__file__),
            "scratch",
            "test_out.pdf"
        )

        os.makedirs(
            os.path.dirname(output_pdf),
            exist_ok=True
        )

        generate_medical_report(
            driver,
            health,
            prediction,
            hospital,
            ambulance,
            output_pdf
        )

        self.assertTrue(
            os.path.exists(output_pdf)
        )


if __name__ == "__main__":
    unittest.main()