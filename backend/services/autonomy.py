"""Opt-in, workload-attributed recovery runbooks. No namespace-wide target guessing."""

import asyncio
import math
import re
import time
from datetime import UTC, datetime

import httpx
from fastapi import HTTPException


class Autonomy:
    def __init__(self, platform):
        self.p = platform
        self.streaks = {}
        self.evidence = {}
        self.status = {}
        self.last_sample = {}

    async def run(self):
        # Verification can wait for new scrapes without blocking the dashboard collector.
        while True:
            await self.tick()
            await asyncio.sleep(self.p.settings.poll_seconds)

    @property
    def enabled(self):
        p = self.p
        return (
            p.settings.allow_automatic and p.settings.healing_mode == "automatic" and not p.paused
        )

    async def observe(self, target):
        from services.k8s_service import KubernetesAdapter
        from services.platform import SSL_CONTEXT, now

        snapshot = await asyncio.to_thread(
            lambda: KubernetesAdapter(self.p.settings.namespace).autonomous_snapshot(target)
        )
        pods = snapshot["pods"]
        if not pods or any(not re.fullmatch(r"[a-z0-9-]+", name) for name in pods):
            raise ValueError("Invalid owned Pod names")
        scope = f'namespace="{self.p.settings.namespace}",pod=~"{"|".join(pods)}"'
        cpu = f'container_cpu_usage_seconds_total{{{scope},container!="",container!="POD"}}'
        mem = f'container_memory_working_set_bytes{{{scope},container!="",container!="POD"}}'
        restarts = f"kube_pod_container_status_restarts_total{{{scope}}}"
        limits = f'kube_pod_container_resource_limits{{{scope},resource="cpu"}}'
        memory_limits = f'kube_pod_container_resource_limits{{{scope},resource="memory"}}'
        # Require all owned pods in every source and joined CPU calculation.
        # Max source age prevents a fresh query timestamp from hiding stale scrapes.
        queries = {
            "cpu_usage": f"max(rate({cpu}[1m]) / on(namespace,pod,container) {limits})",
            "pod_restarts": f"sum(increase({restarts}[1m]))",
            "memory_usage": f"max({mem} / on(namespace,pod,container) {memory_limits})",
            "containers_cpu": f"count({cpu})",
            "containers_cpu_joined": f"count(rate({cpu}[1m]) / on(namespace,pod,container) {limits})",
            "containers_memory": f"count({mem})",
            "containers_memory_joined": f"count({mem} / on(namespace,pod,container) {memory_limits})",
        }
        for key, expression in {
            "cpu": cpu,
            "memory": mem,
            "restarts": restarts,
            "limits": limits,
            "memory_limits": memory_limits,
            "joined": f"rate({cpu}[1m]) / on(namespace,pod,container) {limits}",
        }.items():
            queries[f"coverage_{key}"] = f"count(count by(pod) ({expression}))"
            if key != "joined":
                queries[f"age_{key}"] = f"max(time() - timestamp({expression}))"
        values = {}
        epochs = []
        async with httpx.AsyncClient(verify=SSL_CONTEXT, trust_env=False, timeout=4) as client:
            for key, query in queries.items():
                response = await client.get(
                    f"{self.p.settings.prometheus_url}/api/v1/query", params={"query": query}
                )
                response.raise_for_status()
                data = response.json()
                rows = data["data"]["result"]
                if data.get("status") != "success" or len(rows) != 1:
                    raise ValueError("Missing or ambiguous workload telemetry")
                stamp, raw = rows[0]["value"]
                value = float(raw)
                if not math.isfinite(value) or not -5 <= time.time() - float(stamp) <= 60:
                    raise ValueError("Invalid or stale telemetry")
                values[key] = value
                if key.startswith("age_"):
                    epochs.append(round(float(stamp) - value, 2))
        if any(values[k] != len(pods) for k in values if k.startswith("coverage_")):
            raise ValueError("Incomplete owned-Pod telemetry coverage")
        if (
            values["containers_cpu"] != values["containers_cpu_joined"]
            or values["containers_memory"] != values["containers_memory_joined"]
        ):
            raise ValueError("Missing container limits or rate samples")
        if any(not 0 <= values[k] <= 60 for k in values if k.startswith("age_")):
            raise ValueError("Stale source samples")
        if any(values[k] < 0 for k in ("cpu_usage", "pod_restarts", "memory_usage")):
            raise ValueError("Negative workload measurement")
        if time.time() - min(epochs) > 60:
            raise ValueError("Evidence expired while collecting measurements")
        return {
            **snapshot,
            "timestamp": now(),
            "source_epoch": min(epochs),
            "memory_usage": values["memory_usage"],
            "cpu_usage": values["cpu_usage"],
            "pod_restarts": values["pod_restarts"],
        }

    def choose(self, evidence):
        # These explainable runbooks do not claim a learned model diagnosed a cause.
        if evidence["pod_restarts"] > 5:
            return "restart_deployment", None
        if evidence["cpu_usage"] > 0.8 and evidence["replicas"] < self.p.settings.max_replicas:
            return "scale_deployment", evidence["replicas"] + 1
        return None

    def permits(self, item):
        evidence = self.evidence.get(item["target"])
        return bool(
            self.enabled
            and self.p.settings.mode == "live"
            and item.get("autonomous")
            and item["actor"] == "autonomous-controller"
            and item["target"] in self.p.settings.automatic_targets
            and evidence
            and item.get("evidence") == evidence
            and 0
            <= (datetime.now(UTC) - datetime.fromisoformat(evidence["timestamp"])).total_seconds()
            <= max(10, self.p.settings.poll_seconds * 2)
            and self.choose(evidence) == (item["action"], item["replicas"])
        )

    async def verify(self, item):
        """Require two healthy observations after verified rollout; bounded timeout."""
        deadline = time.monotonic() + self.p.settings.automatic_verify_seconds
        healthy = 0
        previous_epoch = None
        while time.monotonic() < deadline:
            if not self.enabled:
                raise ValueError("Recovery verification interrupted by policy pause")
            await asyncio.sleep(self.p.settings.poll_seconds)
            evidence = await self.observe(item["target"])
            if evidence["uid"] != item["target_uid"]:
                raise ValueError("Deployment identity changed during verification")
            if evidence["source_epoch"] <= datetime.fromisoformat(item["executed_at"]).timestamp():
                continue
            if evidence["source_epoch"] == previous_epoch:
                continue
            previous_epoch = evidence["source_epoch"]
            healthy = healthy + 1 if self.healthy(evidence) else 0
            if healthy >= 2:
                return evidence
        raise TimeoutError("Rollout available but workload telemetry recovery not verified")

    @staticmethod
    def healthy(evidence):
        return (
            evidence["cpu_usage"] <= 0.8
            and evidence["memory_usage"] <= 0.85
            and evidence["pod_restarts"] <= 5
        )

    async def tick(self):
        from services.platform import now

        if not self.enabled or self.p.settings.mode != "live":
            self.streaks.clear()
            self.evidence.clear()
            self.last_sample.clear()
            return
        for target in self.p.settings.automatic_targets:
            if not self.enabled:
                break
            try:
                evidence = await self.observe(target)
                self.evidence[target] = evidence
                if self.last_sample.get(target) == evidence["source_epoch"]:
                    continue
                self.last_sample[target] = evidence["source_epoch"]
                decision = self.choose(evidence)
                state = self.p.store.get("autonomous_state", target) or {}
                if self.healthy(evidence):
                    count = (
                        self.streaks.get(target, ("healthy", 0))[1]
                        if self.streaks.get(target, (None,))[0] == "healthy"
                        else 0
                    )
                    self.streaks[target] = ("healthy", count + 1)
                    if count + 1 >= 2:
                        self.p.store.put(
                            "autonomous_state", dict(id=target, timestamp=now(), latched=False)
                        )
                    self.status[target] = "healthy"
                    continue
                if not decision:
                    self.streaks.pop(target, None)
                    self.status[target] = (
                        "No permitted runbook or replica limit reached; review required"
                    )
                    continue
                if state.get("latched"):
                    self.status[target] = (
                        "Action already attempted for this fault; waiting for healthy evidence"
                    )
                    continue
                key = (decision, evidence["uid"], evidence["generation"], tuple(evidence["pods"]))
                previous, count = self.streaks.get(target, (None, 0))
                count = count + 1 if previous == key else 1
                self.streaks[target] = (key, count)
                self.status[target] = (
                    f"Confirming fault: {count}/{self.p.settings.automatic_confirmations}"
                )
                if count < self.p.settings.automatic_confirmations or not self.enabled:
                    continue
                action, replicas = decision
                item = self.p.recommend(
                    dict(
                        action=action,
                        replicas=replicas,
                        target=target,
                        namespace=self.p.settings.namespace,
                        rationale=f"Confirmed workload rule: CPU {evidence['cpu_usage']:.3g}, restarts/min {evidence['pod_restarts']:.3g}; {count} consecutive observations",
                    ),
                    "autonomous-controller",
                )
                if item["actor"] != "autonomous-controller" or item["status"] != "recommended":
                    self.status[target] = "Existing operator action requires review"
                    continue
                item.update(
                    autonomous=True,
                    target_uid=evidence["uid"],
                    target_generation=evidence["generation"],
                    evidence=evidence,
                )
                self.p.store.put("actions", item)
                if not any(
                    a.get("correlation_id") == item["correlation_id"]
                    for a in self.p.store.list("alerts")
                ):
                    self.p.record(
                        "alerts",
                        severity="high",
                        message=item["rationale"],
                        status="open",
                        target=target,
                        correlation_id=item["correlation_id"],
                        dedupe_key=f"autonomous:{target}",
                    )
                result = await self.p.execute(item["id"], "policy-engine")
                self.status[target] = result["status"]
            except HTTPException as exc:
                self.status[target] = str(exc.detail)
            except Exception as exc:
                self.streaks.pop(target, None)
                self.evidence.pop(target, None)
                self.status[target] = (
                    f"Blocked: {type(exc).__name__}; check ownership and fresh telemetry"
                )
