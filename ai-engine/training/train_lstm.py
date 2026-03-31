"""Train LSTM Failure Prediction Model"""
import numpy as np
import os

try:
    import tensorflow as tf
    from tensorflow.keras.models import Sequential
    from tensorflow.keras.layers import LSTM, Dense, Dropout, Input
    TF_AVAILABLE = True
except ImportError:
    TF_AVAILABLE = False
    print("⚠️ TensorFlow not installed. Run: pip install tensorflow")

if TF_AVAILABLE:
    print("🚀 Training LSTM Failure Prediction Model...")
    np.random.seed(42)
    SEQ_LEN = 60   # 60 timesteps
    FEATURES = 4   # cpu, memory, restarts, latency
    N_SAMPLES = 500

    # Synthetic sequences
    X = np.random.uniform(0.1, 1.0, (N_SAMPLES, SEQ_LEN, FEATURES)).astype(np.float32)
    # Label: failure_prob = avg of last 10 cpu+mem readings
    y_prob = np.mean(X[:, -10:, :2], axis=(1, 2)).reshape(-1, 1)
    y_ttf  = ((1 - y_prob) * 120).reshape(-1, 1)  # minutes to failure
    y = np.hstack([y_prob, y_ttf]).astype(np.float32)

    # Build LSTM model
    model = Sequential([
        Input(shape=(SEQ_LEN, FEATURES)),
        LSTM(64, return_sequences=True),
        Dropout(0.2),
        LSTM(32),
        Dropout(0.2),
        Dense(16, activation='relu'),
        Dense(2, activation='sigmoid')
    ])
    model.compile(optimizer='adam', loss='mse', metrics=['mae'])
    model.summary()

    history = model.fit(X, y, epochs=20, batch_size=32, validation_split=0.2, verbose=1)

    os.makedirs("prediction_model/models", exist_ok=True)
    model.save("prediction_model/models/lstm_model.h5")
    print("✅ LSTM model saved to prediction_model/models/lstm_model.h5")
    print(f"Final MAE: {history.history['mae'][-1]:.4f}")
