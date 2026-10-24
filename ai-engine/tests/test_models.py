import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pytest
from anomaly_detection.detector import AnomalyDetector, train, validate
from fastapi.testclient import TestClient
from main import app
from prediction_model.predictor import forecast


def test_missing_model_rules(tmp_path):
    d = AnomalyDetector(tmp_path)
    assert not d.is_loaded()
    r = d.detect([[0.96, 0.4, 1, 50]])
    assert r["source"] == "rule-based" and r["anomaly_score"] is None
    assert r["observations"][0]["feature"] == "cpu_usage"


@pytest.mark.parametrize(
    "x",
    [
        [],
        [[1, 2]],
        [[float("nan"), 0.4, 1, 10]],
        [[0.2, 0.4, -1, 10]],
        [[0.2, 0.4, 1.2, 10]],
        [[0.2, 0.4, 1, 70000]],
    ],
)
def test_invalid(x):
    with pytest.raises(ValueError):
        validate(x)


def test_training_reproducibility(tmp_path):
    first = train(tmp_path / "a")
    second = train(tmp_path / "b")
    assert first == second
    a, b = AnomalyDetector(tmp_path / "a"), AnomalyDetector(tmp_path / "b")
    assert a.detect([[0.96, 0.95, 12, 840]]) == b.detect([[0.96, 0.95, 12, 840]])
    assert a.detect([[0.96, 0.95, 12, 840]])["is_anomaly"]
    assert a.model.named_steps["scale"].n_features_in_ == 4
    assert first["evaluation"]["recall"] > 0.8


def test_chronological_forecast():
    seq = [[0.2 + i * 0.01, 0.3 + i * 0.005, 1, 42] for i in range(12)]
    r = forecast(seq, [i * 5 for i in range(12)])
    assert r["model"] == "linear-trend-baseline"
    assert r["forecast"]["cpu_usage"] == pytest.approx(0.32)
    assert r["horizon_seconds"] == 5 and r["failure_probability"] is None
    assert r["evaluation"]["linear_mae_fraction"] < r["evaluation"]["persistence_mae_fraction"]
    with pytest.raises(ValueError):
        forecast(seq, [0] * 12)
    with pytest.raises(ValueError):
        forecast(seq[:3], [0, 5, 10])


def test_api():
    with TestClient(app) as c:
        assert (
            c.post(
                "/detect",
                json={
                    "cpu_usage": 2,
                    "memory_usage": 0.2,
                    "pod_restarts": 1,
                    "network_latency": 40,
                },
            ).status_code
            == 422
        )
        assert c.post("/predict", json={"sequence": [], "timestamps": []}).status_code == 422
        assert c.post("/detect", content="x" * 70000).status_code == 413
        assert c.get("/model-status").json()["prediction"]["failure_probability_available"] is False


def test_corrupt_model_falls_back(tmp_path):
    (tmp_path / "metadata.json").write_text("invalid json")
    (tmp_path / "detector.joblib").write_bytes(b"broken")
    detector = AnomalyDetector(tmp_path)
    assert detector.detect([[0.3, 0.4, 1, 42]])["source"] == "rule-based"
    assert "could not be loaded" in detector.metadata["load_status"]


def test_threshold_guard_catches_isolated_cpu_spike(tmp_path):
    train(tmp_path)
    detector = AnomalyDetector(tmp_path)
    result = detector.detect([[0.96, 0.48, 1, 42]])
    assert result["is_anomaly"]
    assert result["source"] == "hybrid"
    assert result["rule_triggered"] is True
    assert result["ml_is_anomaly"] is False
    assert result["anomaly_score"] > 0
    assert "within learned baseline" in result["explanation"]
