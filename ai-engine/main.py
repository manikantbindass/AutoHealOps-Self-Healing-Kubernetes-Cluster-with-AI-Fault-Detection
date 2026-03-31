"""AutoHealOps AI Engine - Anomaly Detection + Failure Prediction Service"""
from fastapi import FastAPI
import uvicorn
from anomaly_detection.detector import AnomalyDetector
from prediction_model.predictor import FailurePredictor
import numpy as np
from pydantic import BaseModel
from typing import List

app = FastAPI(title="AutoHealOps AI Engine", version="1.0.0")
detector = AnomalyDetector()
predictor = FailurePredictor()

class MetricInput(BaseModel):
    cpu_usage: float
    memory_usage: float
    pod_restarts: int
    network_latency: float

class TimeSeriesInput(BaseModel):
    sequence: List[List[float]]  # shape: [timesteps, features]

@app.get("/")
def root():
    return {"service": "AutoHealOps AI Engine", "status": "running"}

@app.post("/detect")
def detect_anomaly(data: MetricInput):
    """Run anomaly detection on current metrics"""
    features = [[data.cpu_usage, data.memory_usage, data.pod_restarts, data.network_latency]]
    score = detector.predict(features)
    return {
        "is_anomaly": bool(score[0] == -1),
        "anomaly_score": float(score[0]),
        "severity": detector.get_severity(data.dict())
    }

@app.post("/predict")
def predict_failure(data: TimeSeriesInput):
    """Predict failure probability from time-series data"""
    sequence = np.array(data.sequence)
    result = predictor.predict(sequence)
    return {
        "failure_probability": float(result["probability"]),
        "time_to_failure_minutes": float(result["time_to_failure"]),
        "confidence": float(result["confidence"])
    }

@app.get("/model-status")
def model_status():
    """Check if models are loaded"""
    return {
        "anomaly_model": detector.is_loaded(),
        "prediction_model": predictor.is_loaded()
    }

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=True)
