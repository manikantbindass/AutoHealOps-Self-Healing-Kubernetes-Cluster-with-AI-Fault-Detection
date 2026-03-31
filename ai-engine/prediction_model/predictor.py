"""LSTM-based Failure Predictor"""
import numpy as np
import os

MODEL_PATH = os.path.join(os.path.dirname(__file__), "models", "lstm_model.h5")

class FailurePredictor:
    def __init__(self):
        self.model = None
        self._load_model()

    def _load_model(self):
        if os.path.exists(MODEL_PATH):
            try:
                import tensorflow as tf
                self.model = tf.keras.models.load_model(MODEL_PATH)
                print("✅ LSTM prediction model loaded")
            except Exception as e:
                print(f"⚠️ LSTM model load failed: {e}. Using heuristic fallback.")
        else:
            print("⚠️ LSTM model not found. Run training/train_lstm.py to train it.")

    def predict(self, sequence: np.ndarray) -> dict:
        """Predict failure probability from metric sequence"""
        if self.model is not None:
            try:
                seq = sequence.reshape(1, sequence.shape[0], sequence.shape[1])
                output = self.model.predict(seq, verbose=0)[0]
                return {
                    "probability": float(output[0]),
                    "time_to_failure": float(output[1]) * 60,
                    "confidence": 0.85
                }
            except Exception:
                pass
        # Heuristic fallback
        latest = sequence[-1] if len(sequence) > 0 else [0.5, 0.5, 2, 100]
        cpu, mem = float(latest[0]), float(latest[1])
        prob = min(1.0, (cpu * 0.4 + mem * 0.4 + 0.2))
        ttf = max(5, (1 - prob) * 120)
        return {"probability": round(prob, 3), "time_to_failure": round(ttf, 1), "confidence": 0.6}

    def is_loaded(self) -> bool:
        return self.model is not None
