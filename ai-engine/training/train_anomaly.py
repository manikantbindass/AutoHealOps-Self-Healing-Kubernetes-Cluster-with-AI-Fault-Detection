"""Train Isolation Forest anomaly detection model"""
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report
import joblib
import os

print("🚀 Training Anomaly Detection Model (Isolation Forest)...")

# Generate synthetic training data
np.random.seed(42)
n_normal = 2000
n_anomaly = 100

# Normal operational metrics
X_normal = np.column_stack([
    np.random.normal(0.35, 0.10, n_normal),    # cpu_usage
    np.random.normal(0.45, 0.10, n_normal),    # memory_usage
    np.random.poisson(1.0, n_normal),           # pod_restarts
    np.random.normal(100, 20, n_normal),        # network_latency_ms
])

# Anomalous metrics (high values)
X_anomaly = np.column_stack([
    np.random.uniform(0.85, 1.0, n_anomaly),
    np.random.uniform(0.80, 1.0, n_anomaly),
    np.random.randint(8, 20, n_anomaly),
    np.random.uniform(600, 2000, n_anomaly),
])

X_train = X_normal  # Train only on normal data (unsupervised)
X_test = np.vstack([X_normal[:200], X_anomaly])
y_test = np.array([1] * 200 + [-1] * n_anomaly)

# Train model
model = IsolationForest(contamination=0.05, n_estimators=200, random_state=42)
model.fit(X_train)

# Evaluate
y_pred = model.predict(X_test)
print("\n📊 Model Evaluation:")
print(classification_report(y_test, y_pred, target_names=["Anomaly", "Normal"]))

# Save model
os.makedirs("anomaly_detection/models", exist_ok=True)
joblib.dump(model, "anomaly_detection/models/isolation_forest.pkl")
print("✅ Model saved to anomaly_detection/models/isolation_forest.pkl")
