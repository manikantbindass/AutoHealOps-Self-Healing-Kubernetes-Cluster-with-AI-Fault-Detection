"""Generate optional, deterministic feature-schema CSV; never labelled failure probabilities."""

import csv
from datetime import UTC, datetime, timedelta
from pathlib import Path

import numpy as np

rng = np.random.default_rng(42)
output = Path(__file__).resolve().parents[1] / "data/synthetic-telemetry.csv"
output.parent.mkdir(exist_ok=True)
with output.open("w", newline="", encoding="utf-8") as handle:
    writer = csv.writer(handle)
    writer.writerow(
        ["timestamp", "cpu_usage", "memory_usage", "pod_restarts", "network_latency", "source"]
    )
    for i in range(1000):
        cpu = float(rng.uniform(0.15, 0.65))
        memory = float(rng.uniform(0.25, 0.7))
        restarts = int(rng.poisson(0.5))
        latency = float(rng.uniform(15, 180))
        if 500 <= i < 520:
            cpu = 0.96
            restarts = 12
        writer.writerow(
            [
                (datetime(2026, 1, 1, tzinfo=UTC) + timedelta(seconds=i * 5)).isoformat(),
                cpu,
                memory,
                restarts,
                latency,
                "synthetic",
            ]
        )
print(f"Synthetic feature CSV created: {output}")
