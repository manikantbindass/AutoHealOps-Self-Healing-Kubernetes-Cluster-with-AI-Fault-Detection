"""Isolation Forest with a persisted preprocessing pipeline; no training on import."""

import json
import os
from pathlib import Path

import joblib
import numpy as np
import sklearn
from sklearn.ensemble import IsolationForest
from sklearn.metrics import precision_recall_fscore_support
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

FEATURES = ["cpu_usage", "memory_usage", "pod_restarts", "network_latency"]
BASELINES = [0.8, 0.85, 5, 500]
ARTIFACTS = Path(os.getenv("MODEL_DIR", str(Path(__file__).resolve().parents[1] / "artifacts")))


def validate(features):
    x = np.asarray(features, dtype=float)
    if x.ndim != 2 or x.shape[1] != 4 or not 1 <= len(x) <= 1000 or not np.isfinite(x).all():
        raise ValueError("Expected 1–1000 finite rows with four ordered features")
    if (
        (x < 0).any()
        or (x[:, :2] > 1).any()
        or (x[:, 2] > 100000).any()
        or (x[:, 3] > 60000).any()
        or not np.equal(x[:, 2], np.floor(x[:, 2])).all()
    ):
        raise ValueError("CPU/memory fractions, integer restarts and latency ms outside bounds")
    return x


def train(output=ARTIFACTS):
    rng = np.random.default_rng(42)
    normal = np.column_stack(
        [
            rng.uniform(0.15, 0.65, 2400),
            rng.uniform(0.25, 0.7, 2400),
            rng.poisson(0.5, 2400),
            rng.uniform(15, 180, 2400),
        ]
    )
    pipeline = Pipeline(
        [
            ("scale", StandardScaler()),
            (
                "isolation_forest",
                IsolationForest(n_estimators=100, contamination=0.03, random_state=42, n_jobs=1),
            ),
        ]
    )
    pipeline.fit(normal[:1800])
    anomalies = np.column_stack(
        [
            rng.uniform(0.86, 1, 200),
            rng.uniform(0.88, 1, 200),
            rng.integers(8, 20, 200),
            rng.uniform(600, 1800, 200),
        ]
    )
    test = np.vstack([normal[1800:], anomalies])
    labels = np.r_[np.zeros(600), np.ones(200)]
    predicted = (pipeline.predict(test) == -1).astype(int)
    precision, recall, f1, _ = precision_recall_fscore_support(
        labels, predicted, average="binary", zero_division=0
    )
    metadata = dict(
        model="IsolationForest + StandardScaler",
        version="iforest-synthetic-v2",
        seed=42,
        features=FEATURES,
        units=["fraction", "fraction", "count / 5 minutes", "ms"],
        training_rows=1800,
        evaluation_rows=800,
        data_source="synthetic independent held-out samples",
        sklearn_version=sklearn.__version__,
        evaluation={"precision": float(precision), "recall": float(recall), "f1": float(f1)},
        limitations="Synthetic evaluation does not establish real-cluster accuracy. Decision score is not failure probability.",
    )
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    joblib.dump(pipeline, output / "detector.joblib")
    (output / "metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    return metadata


class AnomalyDetector:
    def __init__(self, directory=ARTIFACTS):
        self.model = None
        self.metadata = {
            "model": "threshold-rules",
            "version": "rules-2.0",
            "features": FEATURES,
            "limitations": "Rule thresholds; no learned baseline",
        }
        directory = Path(directory)
        # Only load trusted local artifacts. joblib is not a safe interchange format.
        if (directory / "detector.joblib").exists() and (directory / "metadata.json").exists():
            try:
                metadata = json.loads((directory / "metadata.json").read_text(encoding="utf-8"))
                if (
                    metadata.get("features") == FEATURES
                    and metadata.get("sklearn_version") == sklearn.__version__
                ):
                    self.model = joblib.load(directory / "detector.joblib")
                    self.metadata = metadata
                else:
                    self.metadata["load_status"] = "incompatible artifact; rules active"
            except Exception:
                self.model = None
                self.metadata["load_status"] = "artifact could not be loaded; rules active"

    def detect(self, features):
        x = validate(features)
        row = x[0]
        observations = [
            dict(
                feature=key,
                value=float(value),
                baseline=baseline,
                explanation=f"{key} {value:.3g} exceeds threshold {baseline}",
            )
            for key, value, baseline in zip(FEATURES, row, BASELINES)
            if value > baseline
        ]
        ml_anomaly = bool(self.model.predict(x)[0] == -1) if self.model is not None else None
        rule_triggered = bool(observations)
        abnormal = bool(ml_anomaly or rule_triggered)
        explanation = "; ".join(o["explanation"] for o in observations) or (
            "Unusual joint feature distribution relative to synthetic training baseline"
            if abnormal
            else "Measurements within baseline"
        )
        if self.model is not None and rule_triggered:
            explanation += (
                "; threshold guard triggered (Isolation Forest decision: "
                + ("anomaly" if ml_anomaly else "within learned baseline")
                + ")"
            )
        return dict(
            is_anomaly=abnormal,
            ml_is_anomaly=ml_anomaly,
            rule_triggered=rule_triggered,
            anomaly_score=float(self.model.decision_function(x)[0])
            if self.model is not None
            else None,
            severity="critical" if row[0] > 0.9 or row[1] > 0.9 else "high" if abnormal else "low",
            observations=observations,
            explanation=explanation,
            model=self.metadata["model"]
            + (" + threshold guards" if self.model is not None else ""),
            model_version=self.metadata["version"]
            + ("+rules-2.0" if self.model is not None else ""),
            source="hybrid"
            if self.model is not None and rule_triggered
            else "machine-learning"
            if self.model is not None
            else "rule-based",
        )

    def is_loaded(self):
        return self.model is not None
