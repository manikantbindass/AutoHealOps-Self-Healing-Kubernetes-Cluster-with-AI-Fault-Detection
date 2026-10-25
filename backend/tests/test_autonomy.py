"""Controller and adapter contracts; these are not real-cluster acceptance tests."""

import asyncio
import sys
import time
from pathlib import Path
from types import SimpleNamespace as NS
from unittest.mock import AsyncMock, Mock

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import Settings
from services.platform import Platform, now
from services import autonomy, k8s_service


@pytest.fixture
def platform(tmp_path):
    p = Platform(
        Settings(
            sqlite_path=str(tmp_path / "auto.sqlite"),
            allow_automatic=True,
            healing_mode="automatic",
            automatic_targets=["checkout-service"],
            poll_seconds=1,
            automatic_verify_seconds=10,
        )
    )
    # Avoid a Mongo dependency in contract tests; production live startup requires it.
    p.settings.mode = "live"
    p.paused = False
    p.workloads = [
        dict(name="checkout-service", namespace="autohealops", kind="Deployment", managed=True)
    ]
    p.sample = AsyncMock()
    yield p
    p.store.close()


def evidence(epoch=1, **kwargs):
    return dict(
        uid="deployment-uid",
        generation=2,
        replicas=3,
        pods=["checkout-abc-123"],
        timestamp=now(),
        source_epoch=epoch,
        cpu_usage=0.96,
        memory_usage=0.5,
        pod_restarts=0,
        **kwargs,
    )


def observations(p, *, restart=False):
    count = 0

    async def observe(target):
        nonlocal count
        count += 1
        value = evidence(count)
        if restart:
            value.update(cpu_usage=0.5, pod_restarts=8)
        return value

    p.autonomy.observe = observe


@pytest.mark.parametrize("restart", [False, True])
def test_confirmed_fault_executes_without_approval_and_latches(platform, restart):
    p = platform
    observations(p, restart=restart)

    async def run():
        for _ in range(2):
            await p.autonomy.tick()
        assert not p.store.list("actions")
        await p.autonomy.tick()
        item = p.store.list("actions")[0]
        assert item["status"] == "dry_run"
        assert item["approved_by"] is None
        assert item["action"] == ("restart_deployment" if restart else "scale_deployment")
        assert item["replicas"] == (None if restart else 4)
        assert item["before"]["uid"] == "deployment-uid"
        for _ in range(5):
            await p.autonomy.tick()
        assert len(p.store.list("actions")) == 1
        assert p.store.get("autonomous_state", "checkout-service")["latched"]

    asyncio.run(run())


def test_same_scrape_pause_and_missing_data_do_not_confirm(platform):
    p = platform
    p.autonomy.observe = AsyncMock(return_value=evidence())

    async def run():
        for _ in range(5):
            await p.autonomy.tick()
        assert not p.store.list("actions")
        p.paused = True
        await p.autonomy.tick()
        assert not p.autonomy.streaks
        p.paused = False
        p.autonomy.observe = AsyncMock(side_effect=ValueError("missing telemetry"))
        await p.autonomy.tick()
        assert not p.autonomy.evidence
        assert "Blocked" in p.autonomy.status["checkout-service"]

    asyncio.run(run())


@pytest.mark.parametrize("recover", [False, True])
def test_live_action_requires_verified_telemetry_or_opens_circuit(platform, monkeypatch, recover):
    p = platform
    p.settings.dry_run = False
    observations(p)
    adapter = NS(execute=Mock(return_value={"verified": True}))
    monkeypatch.setattr(k8s_service, "KubernetesAdapter", lambda ns: adapter)
    p.autonomy.verify = (
        AsyncMock(return_value=evidence(4)) if recover else AsyncMock(side_effect=TimeoutError())
    )

    async def run():
        for _ in range(3):
            await p.autonomy.tick()
        item = p.store.list("actions")[0]
        adapter.execute.assert_called_once()
        assert item["status"] == ("succeeded" if recover else "failed")
        assert p.paused is (not recover)
        alert = p.store.list("alerts")[0]
        assert alert["status"] == ("resolved" if recover else "open")
        if recover:
            assert item["result"]["telemetry_verified"]
        else:
            assert any(a["action"] == "autonomy_circuit_open" for a in p.store.list("audit"))

    asyncio.run(run())


@pytest.mark.parametrize("bad", ["missing", "stale", "partial", "nan", "valid"])
def test_prometheus_owned_pod_queries_fail_closed(platform, monkeypatch, bad):
    original = httpx.AsyncClient
    snapshot = dict(uid="u", generation=1, replicas=1, pods=["checkout-123"])
    monkeypatch.setattr(
        k8s_service, "KubernetesAdapter", lambda ns: NS(autonomous_snapshot=lambda t: snapshot)
    )

    def response(request):
        q = request.url.params["query"]
        assert 'namespace="autohealops",pod=~"checkout-123"' in q
        value = 1 if q.startswith("count") else 0 if "timestamp(" in q else 0.5
        if bad == "stale" and "timestamp(" in q:
            value = 90
        if bad == "partial" and q.startswith("count"):
            value = 0
        if bad == "nan":
            value = "NaN"
        rows = [] if bad == "missing" else [{"value": [time.time(), str(value)]}]
        return httpx.Response(200, json={"status": "success", "data": {"result": rows}})

    monkeypatch.setattr(
        autonomy.httpx,
        "AsyncClient",
        lambda **kw: original(transport=httpx.MockTransport(response)),
    )
    if bad == "valid":
        assert asyncio.run(platform.autonomy.observe("checkout-service"))["pods"] == [
            "checkout-123"
        ]
        return
    with pytest.raises(ValueError):
        asyncio.run(platform.autonomy.observe("checkout-service"))


def test_verification_needs_distinct_healthy_scrapes(platform, monkeypatch):
    p = platform
    epoch = time.time()
    healthy = evidence(epoch + 1)
    healthy["cpu_usage"] = 0.4
    p.autonomy.observe = AsyncMock(
        side_effect=[healthy, healthy, {**healthy, "source_epoch": epoch + 2}]
    )
    monkeypatch.setattr(autonomy.asyncio, "sleep", AsyncMock())
    result = asyncio.run(
        p.autonomy.verify(
            {"target": "checkout-service", "target_uid": "deployment-uid", "executed_at": now()}
        )
    )
    assert result["source_epoch"] == epoch + 2
    assert p.autonomy.observe.await_count == 3


@pytest.mark.parametrize("change", ["label", "uid", "generation", "paused", "hpa"])
def test_adapter_rechecks_authorization_before_patch(change):
    adapter = object.__new__(k8s_service.KubernetesAdapter)
    adapter.namespace = "autohealops"
    d = NS(
        metadata=NS(
            labels={"autohealops.io/managed": "true", "autohealops.io/autonomous": "true"},
            uid="u",
            generation=1,
        ),
        spec=NS(paused=False, replicas=3),
    )
    if change == "label":
        d.metadata.labels.pop("autohealops.io/autonomous")
    if change == "uid":
        d.metadata.uid = "other"
    if change == "generation":
        d.metadata.generation = 2
    if change == "paused":
        d.spec.paused = True
    adapter.autoscaling = NS(
        list_namespaced_horizontal_pod_autoscaler=lambda *a, **kw: NS(
            items=[1] if change == "hpa" else []
        )
    )
    patch = Mock()
    adapter.apps = NS(
        read_namespaced_deployment=lambda *a, **kw: d, patch_namespaced_deployment=patch
    )
    with pytest.raises(ValueError):
        adapter.execute(
            dict(
                namespace="autohealops",
                target="checkout-service",
                action="restart_deployment",
                autonomous=True,
                target_uid="u",
                target_generation=1,
            ),
            5,
        )
    patch.assert_not_called()


def test_exact_target_config_and_manual_defaults(monkeypatch):
    for bad in [".*", "checkout|other", "../checkout"]:
        with pytest.raises(ValueError):
            Settings(automatic_targets=[bad])
    monkeypatch.setenv("AUTOMATIC_TARGETS", "checkout-service,payment-worker")
    assert Settings.from_env().automatic_targets == ["checkout-service", "payment-worker"]
    assert Settings().healing_mode == "manual"
    assert not Settings().allow_automatic


def test_snapshot_uses_controller_uids_not_similar_names():
    adapter = object.__new__(k8s_service.KubernetesAdapter)
    adapter.namespace = "autohealops"

    def owner(kind, uid):
        return NS(kind=kind, uid=uid, controller=True)

    d = NS(
        metadata=NS(
            uid="deploy",
            generation=1,
            labels={"autohealops.io/managed": "true", "autohealops.io/autonomous": "true"},
        ),
        spec=NS(paused=False, replicas=1),
    )
    rs = NS(metadata=NS(uid="rs", owner_references=[owner("Deployment", "deploy")]))
    pods = [
        NS(
            metadata=NS(
                name=name, deletion_timestamp=None, owner_references=[owner("ReplicaSet", uid)]
            )
        )
        for name, uid in [("checkout-owned", "rs"), ("checkout-imposter", "different-rs")]
    ]
    adapter.apps = NS(
        read_namespaced_deployment=lambda *a, **kw: d,
        list_namespaced_replica_set=lambda *a, **kw: NS(items=[rs]),
    )
    adapter.core = NS(list_namespaced_pod=lambda *a, **kw: NS(items=pods))
    adapter.autoscaling = NS(
        list_namespaced_horizontal_pod_autoscaler=lambda *a, **kw: NS(items=[])
    )
    assert adapter.autonomous_snapshot("checkout")["pods"] == ["checkout-owned"]


def test_verification_timeout_and_pause_cannot_report_success(platform, monkeypatch):
    p = platform
    p.autonomy.observe = AsyncMock()
    monkeypatch.setattr(autonomy, "time", NS(monotonic=Mock(side_effect=[0, 11])))
    with pytest.raises(TimeoutError):
        asyncio.run(p.autonomy.verify({"target": "checkout-service"}))
    p.autonomy.observe.assert_not_awaited()
    p.paused = True
    monkeypatch.setattr(autonomy, "time", NS(monotonic=Mock(side_effect=[0, 1])))
    with pytest.raises(ValueError, match="pause"):
        asyncio.run(p.autonomy.verify({"target": "checkout-service"}))
