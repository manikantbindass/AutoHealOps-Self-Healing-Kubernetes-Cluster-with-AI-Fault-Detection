"""Metric trend forecast, explicitly not calibrated failure prediction."""

import numpy as np
from anomaly_detection.detector import FEATURES, validate


def forecast(sequence, times):
    x = validate(sequence)
    t = np.asarray(times, dtype=float)
    if (
        not 6 <= len(x) <= 120
        or len(t) != len(x)
        or not np.isfinite(t).all()
        or not (np.diff(t) > 0).all()
    ):
        raise ValueError("Require 6–120 samples and strictly increasing finite timestamps")
    intervals = np.diff(t)
    cadence = float(np.median(intervals))
    if cadence < 1 or cadence > 3600 or np.max(intervals) > cadence * 3:
        raise ValueError("Sample cadence must be 1–3600s without large gaps")
    y = x[:, :2]
    # Expanding chronological holdout: each prediction uses only earlier samples.
    linear_errors, persistence_errors = [], []
    for index in range(max(4, len(y) // 2), len(y)):
        tt = (t[:index] - t[0]) / cadence
        coefficients = np.linalg.lstsq(
            np.column_stack([tt, np.ones(index)]), y[:index], rcond=None
        )[0]
        predicted = np.clip(np.array([(t[index] - t[0]) / cadence, 1]) @ coefficients, 0, 1)
        linear_errors.append(abs(predicted - y[index]))
        persistence_errors.append(abs(y[index - 1] - y[index]))
    linear_mae = float(np.mean(linear_errors))
    baseline_mae = float(np.mean(persistence_errors))
    use_linear = linear_mae < baseline_mae
    tt = (t - t[0]) / cadence
    coefficients = np.linalg.lstsq(np.column_stack([tt, np.ones(len(t))]), y, rcond=None)[0]
    next_value = np.clip(np.array([tt[-1] + 1, 1]) @ coefficients, 0, 1) if use_linear else y[-1]
    return dict(
        available=True,
        model="linear-trend-baseline" if use_linear else "persistence-baseline",
        model_version="forecast-v2",
        horizon_seconds=cadence,
        forecast=dict(zip(FEATURES[:2], map(float, next_value))),
        evaluation={
            "linear_mae_fraction": linear_mae,
            "persistence_mae_fraction": baseline_mae,
            "holdout_samples": len(linear_errors),
            "split": "expanding chronological; no future samples in fitting",
        },
        uncertainty=None,
        failure_probability=None,
        limitations="One-sample CPU/memory forecast. No labelled failure dataset; failure probability, confidence and time-to-failure are unavailable.",
    )


class FailurePredictor:
    def is_loaded(self):
        return False
