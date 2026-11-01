"""
AI Driver Health Guardian — Unified Sensor Manager & Hardware Abstraction Layer

Interface:
  SensorManager
  ├── MAX30102 (HR / SpO2)
  ├── AD8232 (ECG)
  ├── MLX90614 (Body Temperature)
  ├── MPU6050 (Accelerometer / Gyroscope / Impact)
  ├── NEO6M (GPS Lat / Lng)
  └── MQ3 (Alcohol Sensor)

Each sensor implements: initialize(), read(), validate(), status(), close()
Falls back gracefully to clearly labeled DEMO MODE when physical hardware is absent.
"""

import random
import math
import time

class BaseSensor:
    def __init__(self, name: str):
        self.name = name
        self.is_connected = False
        self.mode = "DEMO MODE"

    def initialize(self) -> bool:
        self.is_connected = False
        self.mode = "DEMO MODE"
        return False

    def validate(self, data: dict) -> bool:
        return data is not None

    def status(self) -> dict:
        return {
            "name": self.name,
            "connected": self.is_connected,
            "mode": self.mode
        }

    def close(self):
        pass


class MAX30102Sensor(BaseSensor):
    def __init__(self):
        super().__init__("MAX30102 (HR/SpO2)")

    def read(self) -> dict:
        # Simulated physiological values for DEMO MODE
        hr = round(72 + random.uniform(-3, 3), 1)
        spo2 = round(98 + random.uniform(-1, 1), 1)
        return {"heart_rate": hr, "spo2": min(100.0, spo2), "is_simulated": True}


class AD8232Sensor(BaseSensor):
    def __init__(self):
        super().__init__("AD8232 (ECG)")

    def read(self) -> dict:
        # Generate 100-sample ECG PQRST waveform waveform
        t = np_linspace = [i * 0.01 for i in range(100)]
        ecg_wave = []
        for x in t:
            # Baseline + QRS spike
            val = 0.5 + 0.05 * math.sin(2 * math.pi * x)
            if 0.45 <= x <= 0.55:
                val += 0.8 * math.sin(math.pi * (x - 0.45) / 0.10)
            ecg_wave.append(round(val, 3))
        return {"ecg_signal": ecg_wave, "is_simulated": True}


class MLX90614Sensor(BaseSensor):
    def __init__(self):
        super().__init__("MLX90614 (Body Temp)")

    def read(self) -> dict:
        temp = round(36.6 + random.uniform(-0.2, 0.4), 1)
        return {"temperature": temp, "unit": "Celsius", "is_simulated": True}


class MPU6050Sensor(BaseSensor):
    def __init__(self):
        super().__init__("MPU6050 (Accel/Gyro)")

    def read(self) -> dict:
        accel_z = round(1.0 + random.uniform(-0.05, 0.05), 2)
        return {
            "accel_x": round(random.uniform(-0.1, 0.1), 2),
            "accel_y": round(random.uniform(-0.1, 0.1), 2),
            "accel_z": accel_z,
            "gyro_x": round(random.uniform(-1.0, 1.0), 1),
            "gyro_y": round(random.uniform(-1.0, 1.0), 1),
            "gyro_z": round(random.uniform(-1.0, 1.0), 1),
            "impact_g": accel_z,
            "is_accident": False,
            "is_simulated": True
        }


class NEO6MGpsSensor(BaseSensor):
    def __init__(self):
        super().__init__("NEO-6M (GPS)")

    def read(self) -> dict:
        # Default Erode District Center
        return {
            "latitude": 11.3410 + random.uniform(-0.001, 0.001),
            "longitude": 77.7170 + random.uniform(-0.001, 0.001),
            "speed_kmh": round(random.uniform(30, 45), 1),
            "satellites": 8,
            "is_simulated": True
        }


class MQ3Sensor(BaseSensor):
    def __init__(self):
        super().__init__("MQ-3 (Alcohol)")

    def read(self) -> dict:
        return {"alcohol_level": 0.0, "is_impacting": False, "is_simulated": True}


class SensorManager:
    def __init__(self):
        self.max30102 = MAX30102Sensor()
        self.ad8232 = AD8232Sensor()
        self.mlx90614 = MLX90614Sensor()
        self.mpu6050 = MPU6050Sensor()
        self.gps = NEO6MGpsSensor()
        self.mq3 = MQ3Sensor()

        self.sensors = [self.max30102, self.ad8232, self.mlx90614, self.mpu6050, self.gps, self.mq3]
        self.mode = "DEMO MODE"

    def initialize_all(self):
        print("[SensorManager] Initializing physical sensor hardware drivers...")
        for s in self.sensors:
            s.initialize()
        print(f"[SensorManager] Initialization complete. Mode: {self.mode}")

    def read_all_telemetry(self) -> dict:
        max_data = self.max30102.read()
        ecg_data = self.ad8232.read()
        temp_data = self.mlx90614.read()
        mpu_data = self.mpu6050.read()
        gps_data = self.gps.read()
        mq3_data = self.mq3.read()

        return {
            "mode": self.mode,
            "is_simulated": True,
            "timestamp": time.time(),
            "heart_rate": max_data["heart_rate"],
            "spo2": max_data["spo2"],
            "temperature": temp_data["temperature"],
            "ecg_signal": ecg_data["ecg_signal"],
            "accel": {"x": mpu_data["accel_x"], "y": mpu_data["accel_y"], "z": mpu_data["accel_z"]},
            "gyro": {"x": mpu_data["gyro_x"], "y": mpu_data["gyro_y"], "z": mpu_data["gyro_z"]},
            "impact_g": mpu_data["impact_g"],
            "is_accident": mpu_data["is_accident"],
            "latitude": gps_data["latitude"],
            "longitude": gps_data["longitude"],
            "speed_kmh": gps_data["speed_kmh"],
            "alcohol_level": mq3_data["alcohol_level"]
        }

    def get_status_summary(self) -> list:
        return [s.status() for s in self.sensors]

    def close_all(self):
        for s in self.sensors:
            s.close()

# Global SensorManager singleton
sensor_manager = SensorManager()
