from datetime import datetime
from typing import Generic, TypeVar
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class MetricInput(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False, extra="forbid")
    cpu_usage: float = Field(ge=0, le=1)
    memory_usage: float = Field(ge=0, le=1)
    pod_restarts: int = Field(ge=0, le=100000, strict=True)
    network_latency: float = Field(ge=0, le=60000)


class LoginInput(BaseModel):
    username: str = Field(max_length=64)
    password: str = Field(max_length=256)


class ScenarioInput(BaseModel):
    scenario: Literal["cpu", "memory", "restarts", "latency", "reset"]


class PolicyInput(BaseModel):
    paused: bool
    healing_mode: Literal["recommendation", "manual", "automatic"]


class DecisionInput(BaseModel):
    rationale: str = Field(min_length=5, max_length=500)


class ActionInput(BaseModel):
    action: Literal["restart_deployment", "scale_deployment"]
    namespace: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{0,61}[a-z0-9]$")
    target: str = Field(pattern=r"^[a-z0-9][a-z0-9.-]{0,251}[a-z0-9]$")
    replicas: int | None = Field(default=None, ge=1, le=20)
    rationale: str = Field(min_length=5, max_length=500)


# Stable response schemas used by generated OpenAPI contracts.


class PartialMetrics(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False)
    cpu_usage: float | None = Field(default=None, ge=0, le=1)
    memory_usage: float | None = Field(default=None, ge=0, le=1)
    pod_restarts: int | None = Field(default=None, ge=0, le=100000, strict=True)
    network_latency: float | None = Field(default=None, ge=0, le=60000)


class MetricRecord(PartialMetrics):
    id: str
    timestamp: datetime
    source: Literal["demo", "live"]


class AlertRecord(BaseModel):
    model_config = ConfigDict(extra="allow")
    id: str
    timestamp: datetime
    severity: str
    message: str
    status: Literal["open", "acknowledged", "resolved"]
    target: str
    correlation_id: str
    anomaly_id: str


class AnomalyRecord(BaseModel):
    id: str
    timestamp: datetime
    is_anomaly: bool
    ml_is_anomaly: bool | None = None
    rule_triggered: bool | None = None
    anomaly_score: float | None
    severity: str
    observations: list[dict]
    explanation: str
    model: str
    model_version: str
    source: str
    measurements: PartialMetrics
    target: str
    namespace: str
    correlation_id: str
    source_mode: Literal["demo", "live"]


class AuditRecord(BaseModel):
    id: str
    timestamp: datetime
    actor: str
    action: str
    target: str
    result: str
    rationale: str
    correlation_id: str
    component: str
    severity: str


class ActionRecord(BaseModel):
    model_config = ConfigDict(extra="allow")
    id: str
    timestamp: datetime
    action: Literal["restart_deployment", "scale_deployment"]
    namespace: str
    target: str
    replicas: int | None
    rationale: str
    actor: str
    correlation_id: str
    dedupe_key: str
    status: Literal[
        "recommended", "approved", "executing", "simulated", "dry_run", "succeeded", "failed"
    ]
    before: dict | None
    after: dict | None
    result: str | dict
    attempts: int
    approved_by: str | None
    simulated: bool


T = TypeVar("T")


class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int
    limit: int
    offset: int


class Overview(BaseModel):
    mode: Literal["demo", "live"]
    simulated: bool
    cluster: str
    connection: dict[str, str]
    metrics: MetricRecord | None
    counts: dict[str, int]
    pod_status: dict[str, int]
    active_alerts: int
    anomalies: int
    actions: list[ActionRecord]
    events: list[AuditRecord]
    worker_updated: str | None
    last_error: str | None
    policy: dict
