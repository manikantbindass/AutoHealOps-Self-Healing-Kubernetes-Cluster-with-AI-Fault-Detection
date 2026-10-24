# AI models and evaluation

## Input contract

Ordered features: `cpu_usage` fraction 0–1, `memory_usage` fraction 0–1, `pod_restarts` integer 0–100000, `network_latency` milliseconds 0–60000. The API rejects malformed, missing, out-of-range, NaN and infinite inputs. Detection accepts one row; the internal validator permits at most 1,000. Forecasting requires 6–120 four-feature samples and matching timezone-aware, strictly increasing timestamps. Median cadence must be 1–3600 seconds, with no interval above three times that cadence. HTTP request bodies are bounded to 64 KiB.

## Anomaly detection

`python -m training.train_anomaly` from `ai-engine/` explicitly trains a StandardScaler → IsolationForest pipeline. No training takes place during API import. A fixed NumPy generator seed (42), fixed Isolation Forest seed and single-thread fitting make the synthetic pipeline reproducible. Training uses 1,800 normal samples; independent held-out evaluation contains 600 normal and 200 synthetic anomalies. Metadata records feature order, units, seed, library version, evaluation precision/recall/F1 and synthetic provenance. Persisted artifacts live in ignored `ai-engine/artifacts/`; the Docker image trains during build. Restart the AI service to load a new artifact.

Inference uses the same saved scaler. `decision_function` is an anomaly decision score, not probability. Lower values indicate more unusual observations. Threshold comparisons explain individual high CPU/memory/restart/latency values; a joint-distribution anomaly may have no individual threshold crossing. Severity uses transparent thresholds, not a learned probability calibration. The final decision is the logical OR of the learned detector and threshold guards. When a loaded model is combined with a threshold breach, source is explicitly `hybrid`; `ml_is_anomaly` preserves the actual model decision and `rule_triggered` identifies the rule. The Isolation Forest score is never altered to imply it caught an isolated spike.

If no compatible artifact exists, the service explicitly returns `source=rule-based`, `model=threshold-rules`, version `rules-2.0`, and a null score. If the AI service itself is unavailable, the backend uses the same documented threshold rules and reports the failed integration. No random data is introduced into live mode.

Only load artifacts from a trusted local training job. joblib can execute code. A scikit-learn version mismatch causes fallback instead of blindly loading an incompatible model. Synthetic evaluation does not prove usefulness, precision or recall on production workloads.

## Forecasting versus failure prediction

The original LSTM trained on fabricated labels derived from CPU/memory and returned invented confidence and time-to-failure; those outputs have been removed. `train_lstm.py` now exits with an explanation. TensorFlow and pandas are no longer mandatory dependencies.

`POST /predict` fits a simple least-squares trend and compares it with last-value persistence using an expanding chronological holdout. Every holdout forecast uses only earlier observations; the final model uses available history to forecast CPU and memory one observed cadence ahead. The candidate with lower holdout mean absolute error is chosen. Outputs are bounded fractions. MAE is reported in fraction units, with holdout count and temporal-split method. Evaluation-based selection on a small window is exploratory, not an unbiased benchmark of future performance.

Failure probability, time-to-failure and confidence are unavailable, returned null or omitted. There is no labelled real failure dataset, calibrated classifier, or statistically defensible uncertainty estimate. Add those only after collecting timestamped failure labels and performing a separate chronological test evaluation. `/model-status` reports this limitation and real anomaly model metadata.

## Operations

The AI container is internal to the trusted deployment boundary; localhost exposes documentation for local use. Training is a trusted CLI operation, not an unauthenticated network endpoint. The API uses bounded timeouts and falls back honestly. Keep inference workers resource-limited; no automatic retraining job is scheduled.
