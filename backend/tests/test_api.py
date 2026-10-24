import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from datetime import UTC, datetime

import pytest
from config import Settings
from fastapi.testclient import TestClient
from main import create_app
from schemas import MetricInput
from services.store import Store


@pytest.fixture
def client(tmp_path):
    with TestClient(
        create_app(
            Settings(
                sqlite_path=str(tmp_path / "test.sqlite"),
                ai_url="http://127.0.0.1:1",
                poll_seconds=300,
            )
        )
    ) as c:
        yield c


def test_full_workflow(client):
    assert client.get("/health/ready").status_code == 200
    assert client.get("/api/v1/overview").json()["simulated"]
    assert client.post("/api/v1/demo/scenarios", json={"scenario": "cpu"}).status_code == 200
    client.post("/api/v1/demo/scenarios", json={"scenario": "cpu"})
    actions = client.get("/api/v1/healing/actions").json()["items"]
    assert len(actions) == 1
    item = actions[0]
    path = f"/api/v1/healing/actions/{item['id']}"
    assert client.post(path + "/execute").status_code == 409
    assert (
        client.post(path + "/approve", json={"rationale": "Evidence reviewed"}).status_code == 200
    )
    assert (
        client.put("/api/v1/settings", json={"paused": False, "healing_mode": "manual"}).status_code
        == 200
    )
    result = client.post(path + "/execute").json()
    assert result["status"] == "simulated"
    assert result["before"]["cpu_usage"] == 0.96
    assert result["after"]["cpu_usage"] < 0.8
    assert client.post(path + "/execute").json()["attempts"] == 1
    alert = client.get("/api/v1/alerts").json()["items"][0]
    assert (
        client.post(f"/api/v1/alerts/{alert['id']}/acknowledge").json()["status"] == "acknowledged"
    )
    assert client.post(f"/api/v1/alerts/{alert['id']}/resolve").json()["status"] == "resolved"
    assert any(
        x["action"] == "execute_completed"
        for x in client.get("/api/v1/audit/events").json()["items"]
    )


def test_safety_limits(client):
    assert (
        client.put(
            "/api/v1/settings", json={"paused": False, "healing_mode": "automatic"}
        ).status_code
        == 409
    )
    body = dict(
        action="scale_deployment",
        namespace="autohealops",
        target="checkout-service",
        replicas=10,
        rationale="Need more capacity",
    )
    assert client.post("/api/v1/healing/actions", json=body).status_code == 422
    body.update(replicas=2, namespace="kube-system")
    assert client.post("/api/v1/healing/actions", json=body).status_code == 403
    body.update(namespace="autohealops", action="delete_namespace")
    assert client.post("/api/v1/healing/actions", json=body).status_code == 422
    assert client.post("/heal", json={}).status_code == 404


def test_contracts(client):
    for limit in (0, 201):
        assert client.get(f"/api/v1/alerts?limit={limit}").status_code == 422
    assert client.get("/api/v1/audit/events?since=2026-01-01T00:00:00").status_code == 422
    assert client.post("/api/v1/demo/scenarios", json={"scenario": "delete"}).status_code == 422
    assert (
        client.post(
            "/api/v1/healing/actions/missing/approve", json={"rationale": "valid rationale"}
        ).status_code
        == 404
    )
    assert "X-Request-ID" in client.get("/health/live").headers
    assert "autohealops_requests_total" in client.get("/telemetry").text
    assert client.get("/api/v1/predictions").json()["available"] is False
    assert client.get("/api/v1/metrics?limit=3").json()["limit"] == 3


@pytest.mark.parametrize(
    "values",
    [
        dict(cpu_usage=1.1),
        dict(memory_usage=-1),
        dict(network_latency=float("inf")),
        dict(pod_restarts=1.5),
    ],
)
def test_metric_validation(values):
    with pytest.raises(ValueError):
        MetricInput(
            **(dict(cpu_usage=0.3, memory_usage=0.4, network_latency=42, pod_restarts=1) | values)
        )


def test_auth_roles_rate_limit(tmp_path):
    cfg = Settings(
        environment="production",
        jwt_secret="x" * 48,
        admin_password="a" * 20,
        viewer_password="v" * 20,
        sqlite_path=str(tmp_path / "auth.sqlite"),
        ai_url="http://127.0.0.1:1",
    )
    with TestClient(create_app(cfg)) as c:
        assert c.get("/api/v1/overview").status_code == 401
        token = c.post(
            "/api/v1/auth/login", json={"username": "viewer", "password": "v" * 20}
        ).json()["access_token"]
        h = {"Authorization": f"Bearer {token}"}
        assert c.get("/api/v1/overview", headers=h).status_code == 200
        assert (
            c.put(
                "/api/v1/settings", json={"paused": False, "healing_mode": "manual"}, headers=h
            ).status_code
            == 403
        )
        for _ in range(4):
            c.post("/api/v1/auth/login", json={"username": "bad", "password": "bad"})
        assert (
            c.post("/api/v1/auth/login", json={"username": "bad", "password": "bad"}).status_code
            == 429
        )


def test_secure_config():
    with pytest.raises(ValueError):
        Settings(environment="production")
    with pytest.raises(ValueError):
        Settings(healing_mode="automatic")
    with pytest.raises(ValueError):
        Settings(mode="live", jwt_secret="x" * 48, admin_password="a" * 20)


def test_websocket(client):
    with client.websocket_connect("/api/v1/ws", headers={"origin": "http://localhost:3000"}) as ws:
        value = ws.receive_json()
        assert value["type"] == "operational_update"
        assert value["overview"]["metrics"]["source"] == "demo"
    with (
        pytest.raises(Exception),
        client.websocket_connect("/api/v1/ws", headers={"origin": "https://untrusted.example"}),
    ):
        pass


def test_persistence_retention(tmp_path):
    cfg = Settings(sqlite_path=str(tmp_path / "persist.sqlite"))
    s = Store(cfg)
    s.put(
        "alerts",
        {"id": "one", "timestamp": datetime.now(UTC).isoformat(), "status": "open"},
    )
    s.put("metrics", {"id": "old", "timestamp": "2000-01-01T00:00:00+00:00"})
    s.prune()
    assert s.list("metrics") == []
    s.close()
    s = Store(cfg)
    assert s.get("alerts", "one")["status"] == "open"
    s.close()


def test_cooldown_and_recommendation(client):
    client.post("/api/v1/demo/scenarios", json={"scenario": "cpu"})
    item = client.get("/api/v1/healing/actions").json()["items"][0]
    path = f"/api/v1/healing/actions/{item['id']}"
    client.post(path + "/approve", json={"rationale": "Review evidence"})
    client.put("/api/v1/settings", json={"paused": False, "healing_mode": "recommendation"})
    assert client.post(path + "/execute").status_code == 409
    client.put("/api/v1/settings", json={"paused": False, "healing_mode": "manual"})
    client.post(path + "/execute")
    second = client.post(
        "/api/v1/healing/actions",
        json={
            "action": "restart_deployment",
            "namespace": "autohealops",
            "target": "checkout-service",
            "rationale": "Second recovery test",
        },
    ).json()
    path = f"/api/v1/healing/actions/{second['id']}"
    client.post(path + "/approve", json={"rationale": "Review second operation"})
    assert client.post(path + "/execute").status_code == 429


def test_remediation_failure_is_not_success(client, monkeypatch):
    from services import k8s_service

    client.post("/api/v1/demo/scenarios", json={"scenario": "cpu"})
    item = client.get("/api/v1/healing/actions").json()["items"][0]
    path = f"/api/v1/healing/actions/{item['id']}"
    client.post(path + "/approve", json={"rationale": "Review explicit live failure"})
    client.put("/api/v1/settings", json={"paused": False, "healing_mode": "manual"})
    p = client.app.state.platform
    p.settings.mode = "live"
    p.settings.dry_run = False
    import jwt

    client.headers["Authorization"] = "Bearer " + jwt.encode(
        {"sub": "admin", "role": "admin", "exp": datetime.now(UTC).timestamp() + 300},
        p.settings.jwt_secret,
        algorithm="HS256",
    )

    class Unavailable:
        def __init__(self, *args):
            pass

        def execute(self, *args):
            raise TimeoutError("cluster rejected request")

    monkeypatch.setattr(k8s_service, "KubernetesAdapter", Unavailable)
    result = client.post(path + "/execute").json()
    assert result["status"] == "failed"
    assert "not verified" in result["result"]
    assert client.post(path + "/execute").status_code == 409


def test_live_dry_run_never_calls_mutator(client, monkeypatch):
    from services import k8s_service

    client.post("/api/v1/demo/scenarios", json={"scenario": "cpu"})
    item = client.get("/api/v1/healing/actions").json()["items"][0]
    path = f"/api/v1/healing/actions/{item['id']}"
    client.post(path + "/approve", json={"rationale": "Review dry-run safeguard"})
    client.put("/api/v1/settings", json={"paused": False, "healing_mode": "manual"})
    client.app.state.platform.settings.mode = "live"
    import jwt

    client.headers["Authorization"] = "Bearer " + jwt.encode(
        {"sub": "admin", "role": "admin", "exp": datetime.now(UTC).timestamp() + 300},
        client.app.state.platform.settings.jwt_secret,
        algorithm="HS256",
    )
    monkeypatch.setattr(
        k8s_service, "KubernetesAdapter", lambda *a: pytest.fail("Dry-run invoked Kubernetes")
    )
    assert client.post(path + "/execute").json()["status"] == "dry_run"


def test_notification_validation(monkeypatch):
    from services.notifications import Notifications

    monkeypatch.setenv("SLACK_WEBHOOK_URL", "http://127.0.0.1/private")
    with pytest.raises(ValueError):
        Notifications()
    monkeypatch.setenv("SLACK_WEBHOOK_URL", "")
    n = Notifications()
    assert n.last == {"slack": "not configured", "email": "not configured"}


def test_ownership_and_replica_limit():
    from types import SimpleNamespace as NS

    from services.k8s_service import KubernetesAdapter

    adapter = object.__new__(KubernetesAdapter)
    adapter.namespace = "autohealops"
    adapter.apps = NS(read_namespaced_deployment=lambda *a, **k: NS(metadata=NS(labels={})))
    with pytest.raises(ValueError, match="Namespace"):
        adapter.execute({"namespace": "kube-system"}, 5)
    with pytest.raises(ValueError, match="labelled"):
        adapter.execute({"namespace": "autohealops", "target": "checkout"}, 5)
    adapter.apps = NS(
        read_namespaced_deployment=lambda *a, **k: NS(
            metadata=NS(labels={"autohealops.io/managed": "true"})
        )
    )
    with pytest.raises(ValueError, match="Replica"):
        adapter.execute(
            {
                "namespace": "autohealops",
                "target": "checkout",
                "action": "scale_deployment",
                "replicas": 6,
            },
            5,
        )


def test_automatic_does_not_bypass_operator_recommendation_approval(tmp_path):
    cfg = Settings(
        allow_automatic=True,
        sqlite_path=str(tmp_path / "automatic.sqlite"),
        ai_url="http://127.0.0.1:1",
        poll_seconds=300,
    )
    with TestClient(create_app(cfg)) as c:
        item = c.post(
            "/api/v1/healing/actions",
            json={
                "action": "restart_deployment",
                "namespace": "autohealops",
                "target": "api-gateway",
                "rationale": "Operator requested review",
            },
        ).json()
        c.put("/api/v1/settings", json={"paused": False, "healing_mode": "automatic"})
        assert c.post(f"/api/v1/healing/actions/{item['id']}/execute").status_code == 409


def test_missing_latency_does_not_hide_available_live_metrics(client, monkeypatch):
    import asyncio
    import httpx
    from services import k8s_service
    from services import platform as platform_module

    original = httpx.AsyncClient

    def response(request):
        assert request.url.path == "/api/v1/query", "Incomplete telemetry must not be sent to ML"
        query = request.url.params["query"]
        value = (
            ".93"
            if "container_cpu_usage" in query
            else ".6"
            if "container_memory" in query
            else "1"
        )
        result = [] if "histogram_quantile" in query else [{"value": [0, value]}]
        return httpx.Response(200, json={"data": {"result": result}})

    monkeypatch.setattr(
        platform_module.httpx,
        "AsyncClient",
        lambda **kwargs: original(transport=httpx.MockTransport(response), trust_env=False),
    )

    class Inventory:
        def __init__(self, *args):
            pass

        def workloads(self):
            return []

    monkeypatch.setattr(k8s_service, "KubernetesAdapter", Inventory)
    p = client.app.state.platform
    p.settings.mode = "live"
    asyncio.run(p.sample())
    assert p.current["cpu_usage"] == 0.93
    assert p.current["network_latency"] is None
    assert p.store.list("alerts")[0]["target"] == "namespace aggregate"
    assert p.store.list("actions") == []


def test_invalid_forecast_history_is_not_reported_as_engine_outage(client, monkeypatch):
    import httpx
    from services import platform as platform_module

    original = httpx.AsyncClient
    transport = httpx.MockTransport(
        lambda request: httpx.Response(422, json={"detail": "Sample cadence invalid"})
    )
    monkeypatch.setattr(
        platform_module.httpx,
        "AsyncClient",
        lambda **kwargs: original(transport=transport, trust_env=False),
    )
    result = client.get("/api/v1/predictions").json()
    assert result["available"] is False
    assert result["engine_available"] is True
    assert "failed validation" in result["reason"]
