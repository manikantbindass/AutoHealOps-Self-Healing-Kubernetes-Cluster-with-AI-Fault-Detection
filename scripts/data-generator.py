"""Generate synthetic Kubernetes metrics for training and testing"""
import numpy as np
import pandas as pd
import json
from datetime import datetime, timedelta
import os

print("📦 Generating synthetic Kubernetes metrics dataset...")

np.random.seed(42)
N = 5000  # data points
start = datetime(2025, 1, 1)
timestamps = [start + timedelta(minutes=i * 5) for i in range(N)]

# Normal baseline with some noise
cpu     = np.clip(np.random.normal(0.35, 0.12, N), 0.01, 1.0)
memory  = np.clip(np.random.normal(0.45, 0.10, N), 0.01, 1.0)
restarts = np.clip(np.random.poisson(1, N), 0, 20).astype(float)
latency  = np.clip(np.random.normal(100, 25, N), 10, 2000)

# Inject anomaly windows
for i in [500, 1200, 2500, 3800]:
    cpu[i:i+20]      = np.random.uniform(0.88, 0.99, 20)
    memory[i:i+20]   = np.random.uniform(0.82, 0.99, 20)
    restarts[i:i+20] = np.random.randint(8, 15, 20)
    latency[i:i+20]  = np.random.uniform(600, 1800, 20)

labels = np.where(
    (cpu > 0.8) | (memory > 0.8) | (restarts > 7) | (latency > 500),
    -1, 1
)

df = pd.DataFrame({
    "timestamp": [t.isoformat() for t in timestamps],
    "cpu_usage": cpu.round(4),
    "memory_usage": memory.round(4),
    "pod_restarts": restarts.astype(int),
    "network_latency": latency.round(2),
    "label": labels
})

os.makedirs("data", exist_ok=True)
df.to_csv("data/metrics_dataset.csv", index=False)
print(f"✅ Dataset saved: data/metrics_dataset.csv ({N} records)")
print(f"   Anomalies: {(labels == -1).sum()} | Normal: {(labels == 1).sum()}")
