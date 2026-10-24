"""Run from ai-engine/: python -m training.train_anomaly."""

import json

from anomaly_detection.detector import train

if __name__ == "__main__":
    print(json.dumps(train(), indent=2))
