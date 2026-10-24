"""Validated model inference API. Training is an explicit trusted CLI operation."""

from datetime import datetime
from typing import Annotated

from anomaly_detection.detector import AnomalyDetector
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import Response
from prediction_model.predictor import forecast
from pydantic import BaseModel, ConfigDict, Field, model_validator

app = FastAPI(title="AutoHealOps fault intelligence", version="2.0.0")
detector = AnomalyDetector()


class MetricInput(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False, extra="forbid")
    cpu_usage: float = Field(ge=0, le=1)
    memory_usage: float = Field(ge=0, le=1)
    pod_restarts: int = Field(ge=0, le=100000, strict=True)
    network_latency: float = Field(ge=0, le=60000)


class TimeSeriesInput(BaseModel):
    sequence: Annotated[list[list[float]], Field(min_length=6, max_length=120)]
    timestamps: Annotated[list[datetime], Field(min_length=6, max_length=120)]

    @model_validator(mode="after")
    def check_times(self):
        if any(t.tzinfo is None for t in self.timestamps):
            raise ValueError("UTC/offset-aware timestamps required")
        return self


@app.middleware("http")
async def request_size(request: Request, call_next):
    # Stream the bounded body before Pydantic parsing; Content-Length alone is insufficient.
    body = bytearray()
    async for chunk in request.stream():
        body.extend(chunk)
        if len(body) > 65536:
            return Response("Request too large", status_code=413)
    request._body = bytes(body)
    return await call_next(request)


@app.get("/")
@app.get("/health/live")
def health():
    return {"status": "ok", "version": "2.0.0"}


@app.post("/detect")
def detect(body: MetricInput):
    return detector.detect(
        [[body.cpu_usage, body.memory_usage, body.pod_restarts, body.network_latency]]
    )


@app.post("/predict")
def predict(body: TimeSeriesInput):
    try:
        return forecast(body.sequence, [t.timestamp() for t in body.timestamps])
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from None


@app.get("/model-status")
def status():
    return {
        "anomaly_model_loaded": detector.is_loaded(),
        "anomaly": detector.metadata,
        "prediction": {
            "model": "chronological trend/persistence baseline",
            "trained_failure_model": False,
            "failure_probability_available": False,
            "limitations": "No labelled failure events. LSTM training withheld until suitable data exists.",
        },
    }
