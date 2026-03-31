"""Isolation Forest Anomaly Detector"""
import numpy as np
import joblib
import os
from sklearn.ensemble import IsolationForest

MODEL_PATH = os.path.join(os.path.dirname(__file__), "models", "isolation_forest.pkl")

class AnomalyDetector:
    def __init__(self):
        self.model = None
        self._load_or_create_model()

    def _load_or_create_model(self):
        if os.path.exists(MODEL_PATH):
            self.model = joblib.load(MODEL_PATH)
            print("✅ Anomaly detection model loaded")
        else:
            print("⚠️ No model found. Training a new one with synthetic data...")
            self._train_new_model()

    def _train_new_model(self):
        """Train on synthetic data as fallback"""
        np.random.seed(42)
        X_normal = np.random.normal(
            loc=[0.3, 0.4, 1.0, 100.0],
            scale=[0.1, 0.1, 0.5, 20.0],
            size=(1000, 4)
        )
        self.model = IsolationForest(contamination=0.05, random_state=42, n_estimators=100)
        self.model.fit(X_normal)
        os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
        joblib.dump(self.model, MODEL_PATH)
        print("✅ New model trained and saved")

    def predict(self, features: list) -> np.ndarray:
        """Returns -1 for anomaly, 1 for normal"""
        X = np.array(features)
        return self.model.predict(X)

    def get_severity(self, metrics: dict) -> str:
        """Determine severity based on metric thresholds"""
        cpu = metrics.get("cpu_usage", 0)
        mem = metrics.get("memory_usage", 0)
        restarts = metrics.get("pod_restarts", 0)
        latency = metrics.get("network_latency", 0)
        if cpu > 0.9 or mem > 0.9 or restarts > 10:
            return "CRITICAL"
        elif cpu > 0.75 or mem > 0.75 or restarts > 5 or latency > 500:
            return "HIGH"
        elif cpu > 0.6 or mem > 0.6 or latency > 300:
            return "MEDIUM"
        return "LOW"

    def is_loaded(self) -> bool:
        return self.model is not None
