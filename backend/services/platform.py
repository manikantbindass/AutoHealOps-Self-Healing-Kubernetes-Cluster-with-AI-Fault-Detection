"""Operational state, deterministic demo and guarded remediation state machine."""

import asyncio
import hashlib
import math
import ssl
import uuid
from datetime import UTC, datetime

import certifi
import httpx

from fastapi import HTTPException
from schemas import PartialMetrics

from services.notifications import Notifications
from services.store import Store


SSL_CONTEXT = ssl.create_default_context(cafile=certifi.where())


def now():
    return datetime.now(UTC).isoformat()


def rules(metrics):
    thresholds = {
        "cpu_usage": (0.80, "CPU fraction"),
        "memory_usage": (0.85, "memory fraction"),
        "pod_restarts": (5, "restart count"),
        "network_latency": (500, "latency ms"),
    }
    observations = [
        {
            "feature": k,
            "value": metrics[k],
            "baseline": threshold,
            "explanation": f"{label} {metrics[k]:.3g} exceeds threshold {threshold}",
        }
        for k, (threshold, label) in thresholds.items()
        if metrics[k] is not None and metrics[k] > threshold
    ]
    return dict(
        is_anomaly=bool(observations),
        anomaly_score=None,
        severity="critical"
        if (metrics["cpu_usage"] or 0) > 0.9 or (metrics["memory_usage"] or 0) > 0.9
        else "high"
        if observations
        else "low",
        observations=observations,
        explanation="; ".join(o["explanation"] for o in observations)
        or "Measurements within configured rule thresholds",
        model="threshold-rules",
        model_version="rules-2.0",
        source="rule-based",
    )


class Platform:
    def __init__(self, settings):
        self.settings = settings
        self.notifications = Notifications()
        self.store = Store(settings)
        self.lock = asyncio.Lock()
        self.execution = asyncio.Lock()
        self.clients = set()
        self.tick = 0
        self.scenario = "healthy"
        self.paused = True  # explicit operator resume required even after restart
        self.current = None
        self.workloads = []
        self.integration = {
            "kubernetes": "simulated" if settings.mode == "demo" else "disconnected",
            "prometheus": "unused in demo" if settings.mode == "demo" else "disconnected",
            "ai": "unavailable; rule-based detector",
        }
        self.last_error = None
        self.worker_updated = None
        saved = self.store.list("demo_state")
        if saved and settings.mode == "demo":
            self.scenario = saved[0]["scenario"]

    def record(self, kind, **values):
        return self.store.put(kind, dict(id=str(uuid.uuid4()), timestamp=now(), **values))

    def audit(self, actor, action, target, result, rationale, correlation_id=None, severity="info"):
        return self.record(
            "audit",
            actor=actor,
            action=action,
            target=target,
            result=result,
            rationale=rationale,
            correlation_id=correlation_id or str(uuid.uuid4()),
            component="control-plane",
            severity=severity,
        )

    def demo_sample(self, step):
        m = dict(
            cpu_usage=round(0.34 + 0.09 * math.sin(step / 5), 3),
            memory_usage=round(0.48 + 0.06 * math.cos(step / 7), 3),
            pod_restarts=1,
            network_latency=round(42 + 15 * math.sin(step / 4), 1),
        )
        overrides = {
            "cpu": {"cpu_usage": 0.96},
            "memory": {"memory_usage": 0.95},
            "restarts": {"pod_restarts": 12},
            "latency": {"network_latency": 840},
        }
        m.update(overrides.get(self.scenario, {}))
        return m

    def demo_workloads(self):
        rows = []
        for i, name in enumerate(
            [
                "api-gateway",
                "checkout-service",
                "payment-worker",
                "inventory-api",
                "event-consumer",
                "web-console",
            ]
        ):
            affected = i == 1 and self.scenario != "healthy"
            rows.append(
                dict(
                    id=f"deploy-{i}",
                    name=name,
                    namespace=self.settings.namespace,
                    kind="Deployment",
                    status="Degraded" if affected else "Healthy",
                    replicas=3 if i < 2 else 2,
                    ready=2 if affected else 3 if i < 2 else 2,
                    managed=True,
                )
            )
            for p in range(3 if i < 2 else 2):
                rows.append(
                    dict(
                        id=f"pod-{i}-{p}",
                        name=f"{name}-7d8f-{p}",
                        namespace=self.settings.namespace,
                        kind="Pod",
                        status="Failed"
                        if affected and p == 0 and self.scenario == "restarts"
                        else "Pending"
                        if affected and p == 0
                        else "Running",
                        restarts=12 if affected and self.scenario == "restarts" else 0,
                        node=f"demo-worker-{p % 3 + 1}",
                        managed=True,
                    )
                )
        rows += [
            dict(
                id=f"node-{i}",
                name=f"demo-worker-{i}",
                namespace="cluster",
                kind="Node",
                status="Ready",
                managed=False,
            )
            for i in range(1, 4)
        ]
        rows.append(
            dict(
                id="namespace",
                name=self.settings.namespace,
                namespace=self.settings.namespace,
                kind="Namespace",
                status="Active",
                managed=False,
            )
        )
        return rows

    async def sample(self):
        if self.settings.mode == "demo":
            self.tick += 1
            metrics = self.demo_sample(self.tick)
            self.workloads = self.demo_workloads()
        else:
            from services.k8s_service import KubernetesAdapter

            try:
                self.workloads = await asyncio.to_thread(
                    lambda: KubernetesAdapter(self.settings.namespace).workloads()
                )
                self.integration["kubernetes"] = "connected"
            except Exception:
                self.workloads = []
                self.integration["kubernetes"] = "unavailable"
            queries = {
                "cpu_usage": f'avg(rate(container_cpu_usage_seconds_total{{namespace="{self.settings.namespace}",container!=""}}[5m]) / on(namespace,pod,container) kube_pod_container_resource_limits{{resource="cpu",namespace="{self.settings.namespace}"}})',
                "memory_usage": f'avg(container_memory_working_set_bytes{{namespace="{self.settings.namespace}",container!=""}} / on(namespace,pod,container) kube_pod_container_resource_limits{{resource="memory",namespace="{self.settings.namespace}"}})',
                "pod_restarts": f'sum(increase(kube_pod_container_status_restarts_total{{namespace="{self.settings.namespace}"}}[5m]))',
                "network_latency": f'1000 * histogram_quantile(0.95, sum by(le)(rate(http_request_duration_seconds_bucket{{namespace="{self.settings.namespace}"}}[5m])))',
            }
            metrics = {}
            async with httpx.AsyncClient(verify=SSL_CONTEXT, trust_env=False, timeout=4) as client:
                for key, query in queries.items():
                    try:
                        response = await client.get(
                            f"{self.settings.prometheus_url}/api/v1/query", params={"query": query}
                        )
                        response.raise_for_status()
                        values = response.json()["data"]["result"]
                        if not values:
                            raise ValueError("Missing exporter data")
                        value = float(values[0]["value"][1])
                        if key == "pod_restarts":
                            value = round(value)
                        # Validate each feature independently; one missing exporter must not hide other data.
                        PartialMetrics(**{key: value})
                        metrics[key] = value
                    except Exception:
                        metrics[key] = None
            self.integration["prometheus"] = (
                "connected"
                if all(value is not None for value in metrics.values())
                else "partial or unavailable exporter data"
            )
            if all(value is None for value in metrics.values()):
                self.current = None
                self.worker_updated = now()
                return
        metrics = PartialMetrics(**metrics).model_dump()
        self.current = self.record("metrics", **metrics, source=self.settings.mode)
        detection = rules(metrics)
        try:
            if any(value is None for value in metrics.values()):
                raise ValueError(
                    "Incomplete AI feature set; threshold rules inspect available measurements"
                )
            async with httpx.AsyncClient(verify=SSL_CONTEXT, trust_env=False, timeout=2) as client:
                response = await client.post(f"{self.settings.ai_url}/detect", json=metrics)
                response.raise_for_status()
                value = response.json()
                if not isinstance(value.get("is_anomaly"), bool) or not value.get("model_version"):
                    raise ValueError("Invalid inference response")
                detection = value
                self.integration["ai"] = value["model"]
        except Exception:
            self.integration["ai"] = "unavailable; rule-based detector"
        if detection["is_anomaly"]:
            key = f"{self.scenario if self.settings.mode == 'demo' else 'live'}:{','.join(o['feature'] for o in detection['observations'])}"
            # Suppress duplicate incidents until previous incident is resolved.
            active = [
                x
                for x in self.store.list("alerts")
                if x.get("dedupe_key") == key and x["status"] != "resolved"
            ]
            if not active:
                correlation = str(uuid.uuid4())
                target = (
                    "checkout-service" if self.settings.mode == "demo" else "namespace aggregate"
                )
                event = self.record(
                    "anomalies",
                    **detection,
                    measurements=metrics,
                    target=target,
                    namespace=self.settings.namespace,
                    correlation_id=correlation,
                    source_mode=self.settings.mode,
                )
                self.record(
                    "alerts",
                    severity=detection["severity"],
                    message=detection["explanation"],
                    status="open",
                    target=target,
                    correlation_id=correlation,
                    dedupe_key=key,
                    anomaly_id=event["id"],
                )
                self.audit(
                    "detector",
                    "anomaly_detected",
                    target,
                    "alert opened",
                    detection["explanation"],
                    correlation,
                    detection["severity"],
                )
                if detection["severity"] in ("high", "critical"):
                    delivered = await self.notifications.send(
                        f"AutoHealOps [{self.settings.mode}] {target}: {detection['explanation']} | correlation {correlation}"
                    )
                    if any(value != "not configured" for value in delivered.values()):
                        self.audit(
                            "notifications",
                            "notification_delivery",
                            target,
                            str(delivered),
                            "Optional configured notification adapter",
                            correlation,
                        )
                # Aggregate live telemetry cannot justify selecting a workload.
                if self.settings.mode == "demo":
                    self.recommend(
                        dict(
                            action="restart_deployment",
                            namespace=self.settings.namespace,
                            target=target,
                            replicas=None,
                            rationale=detection["explanation"],
                        ),
                        "detector",
                        correlation,
                    )
        self.worker_updated = now()

    def recommend(self, body, actor, correlation=None):
        if body["namespace"] != self.settings.namespace:
            raise HTTPException(403, "Namespace outside configured boundary")
        workload = next(
            (
                x
                for x in self.workloads
                if x["name"] == body["target"]
                and x["kind"] == "Deployment"
                and x["namespace"] == body["namespace"]
            ),
            None,
        )
        if not workload or not workload.get("managed"):
            raise HTTPException(409, "Target is unavailable or lacks autohealops.io/managed=true")
        if body["action"] == "scale_deployment" and (
            body.get("replicas") is None or not 1 <= body["replicas"] <= self.settings.max_replicas
        ):
            raise HTTPException(422, "Replica count outside configured bounds")
        dedupe = hashlib.sha256(
            f"{body['action']}:{body['namespace']}:{body['target']}:{body.get('replicas')}".encode()
        ).hexdigest()
        for old in self.store.list("actions"):
            if old["dedupe_key"] == dedupe and old["status"] in (
                "recommended",
                "approved",
                "executing",
            ):
                return old
        item = self.record(
            "actions",
            **body,
            actor=actor,
            correlation_id=correlation or str(uuid.uuid4()),
            dedupe_key=dedupe,
            status="recommended",
            before=self.current,
            after=None,
            result="Awaiting operator review",
            attempts=0,
            approved_by=None,
            simulated=self.settings.mode == "demo",
        )
        self.audit(
            actor,
            "recommend",
            body["target"],
            "recommended",
            body["rationale"],
            item["correlation_id"],
        )
        return item

    async def execute(self, action_id, actor):
        async with self.execution:
            item = self.store.get("actions", action_id)
            if not item:
                raise HTTPException(404, "Action not found")
            if item["status"] in ("simulated", "dry_run", "succeeded"):
                return item  # idempotent replay
            if self.paused or self.settings.healing_mode == "recommendation":
                raise HTTPException(409, "Healing paused or recommendation-only")
            if item["status"] != "approved" and not (
                self.settings.healing_mode == "automatic"
                and self.settings.allow_automatic
                and item["action"] == "restart_deployment"
                and item["actor"] == "detector"
                and item["simulated"]
            ):
                raise HTTPException(409, "Explicit approval required")
            if item["attempts"] >= 1:
                raise HTTPException(
                    409, "Retry limit reached; investigate before creating another action"
                )
            previous = [
                x
                for x in self.store.list("actions")
                if x["id"] != item["id"] and x.get("executed_at")
            ]
            recent = [
                x
                for x in previous
                if (datetime.now(UTC) - datetime.fromisoformat(x["executed_at"])).total_seconds()
                < 3600
            ]
            if len(recent) >= 10:
                raise HTTPException(429, "Maximum ten operations per hour")
            if any(
                x["target"] == item["target"]
                and (datetime.now(UTC) - datetime.fromisoformat(x["executed_at"])).total_seconds()
                < self.settings.cooldown_seconds
                for x in recent
            ):
                raise HTTPException(429, "Target cooldown active")
            # Revalidate boundary and ownership immediately before mutation.
            if item["namespace"] != self.settings.namespace or not any(
                x["name"] == item["target"] and x["kind"] == "Deployment" and x.get("managed")
                for x in self.workloads
            ):
                raise HTTPException(409, "Target ownership is no longer valid")
            item.update(
                status="executing",
                attempts=item["attempts"] + 1,
                executed_at=now(),
                before=self.current,
            )
            self.store.put("actions", item)
            self.audit(
                actor,
                "execute_started",
                item["target"],
                "executing",
                item["rationale"],
                item["correlation_id"],
            )
            try:
                if self.settings.mode == "demo":
                    before = self.current
                    self.scenario = "healthy"
                    self.save_demo()
                    await self.sample()
                    item.update(
                        status="simulated",
                        result="Simulated recovery only; no Kubernetes operation performed",
                        before=before,
                        after=self.current,
                    )
                elif self.settings.dry_run:
                    item.update(
                        status="dry_run",
                        result="Policy validated; no Kubernetes mutation performed",
                        after=self.current,
                    )
                else:
                    from services.k8s_service import KubernetesAdapter

                    result = await asyncio.to_thread(
                        lambda: KubernetesAdapter(self.settings.namespace).execute(
                            item, self.settings.max_replicas
                        )
                    )
                    await self.sample()
                    item.update(status="succeeded", result=result, after=self.current)
            except Exception as exc:
                item.update(
                    status="failed",
                    result=f"{type(exc).__name__}: recovery not verified; inspect server logs",
                )
            self.store.put("actions", item)
            self.audit(
                actor,
                "execute_completed",
                item["target"],
                item["status"],
                str(item["result"]),
                item["correlation_id"],
                "error" if item["status"] == "failed" else "info",
            )
            return item

    def save_demo(self):
        self.store.put("demo_state", dict(id="state", timestamp=now(), scenario=self.scenario))

    def overview(self):
        pods = [x for x in self.workloads if x["kind"] == "Pod"]
        return dict(
            mode=self.settings.mode,
            simulated=self.settings.mode == "demo",
            cluster="local-demo" if self.settings.mode == "demo" else self.settings.namespace,
            connection=self.integration,
            metrics=self.current,
            counts={
                kind.lower() + "s": sum(x["kind"] == kind for x in self.workloads)
                for kind in ["Node", "Namespace", "Pod", "Deployment"]
            },
            pod_status={
                s: sum(x["status"] == s for x in pods) for s in ["Running", "Pending", "Failed"]
            },
            active_alerts=sum(x["status"] != "resolved" for x in self.store.list("alerts")),
            anomalies=len(self.store.list("anomalies")),
            actions=self.store.list("actions")[:5],
            events=self.store.list("audit")[:8],
            worker_updated=self.worker_updated,
            last_error=self.last_error,
            policy=self.policy(),
        )

    def policy(self):
        return dict(
            paused=self.paused,
            healing_mode=self.settings.healing_mode,
            dry_run=self.settings.dry_run,
            allow_automatic=self.settings.allow_automatic,
            max_replicas=self.settings.max_replicas,
            cooldown_seconds=self.settings.cooldown_seconds,
            max_actions_per_hour=10,
            retry_limit=1,
            namespace=self.settings.namespace,
        )

    async def run(self):
        while True:
            try:
                async with self.lock:
                    await self.sample()
                    self.store.prune()
                    self.last_error = None
                if (
                    self.settings.healing_mode == "automatic"
                    and self.settings.allow_automatic
                    and not self.paused
                ):
                    for item in self.store.list("actions"):
                        if (
                            item["status"] == "recommended"
                            and item["action"] == "restart_deployment"
                            and item["actor"] == "detector"
                            and item["simulated"]
                        ):
                            try:
                                await self.execute(item["id"], "policy-engine")
                            except HTTPException:
                                pass
                message = {
                    "type": "operational_update",
                    "timestamp": now(),
                    "overview": self.overview(),
                }
                for ws in list(self.clients):
                    try:
                        await asyncio.wait_for(ws.send_json(message), timeout=1)
                    except Exception:
                        self.clients.discard(ws)
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                self.last_error = type(exc).__name__
            await asyncio.sleep(self.settings.poll_seconds)
