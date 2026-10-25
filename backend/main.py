"""AutoHealOps API: explicit provenance, durable events, safe control plane."""

import asyncio
import contextlib
import hmac
import logging
import ssl
import time
import uuid
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta

import certifi
import httpx

import jwt
from config import Settings
from fastapi import Depends, FastAPI, HTTPException, Query, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from schemas import (
    ActionInput,
    ActionRecord,
    AlertRecord,
    AnomalyRecord,
    AuditRecord,
    DecisionInput,
    LoginInput,
    MetricRecord,
    Overview,
    Page,
    PolicyInput,
    ScenarioInput,
)
from services.platform import Platform, now

SSL_CONTEXT = ssl.create_default_context(cafile=certifi.where())


logging.basicConfig(level=logging.INFO, format="%(message)s")
logging.getLogger("httpx").setLevel(logging.WARNING)
log = logging.getLogger("autohealops")
REQUESTS = Counter("autohealops_requests_total", "API requests", ["method", "status"])
LATENCY = Histogram("autohealops_request_duration_seconds", "API latency")
security = HTTPBearer(auto_error=False)


def create_app(settings=None):
    cfg = settings or Settings.from_env()

    @asynccontextmanager
    async def lifespan(app):
        # Database readiness is required; bounded startup retries never log URI credentials.
        for attempt in range(5):
            try:
                app.state.platform = Platform(cfg)
                break
            except Exception:
                if attempt == 4:
                    raise RuntimeError(
                        "Persistence unavailable after five startup attempts"
                    ) from None
                await asyncio.sleep(min(2**attempt, 8))
        p = app.state.platform
        if cfg.mode == "demo" and not p.store.list("metrics"):
            for step in range(-59, 1):
                p.store.put(
                    "metrics",
                    dict(
                        id=str(uuid.uuid4()),
                        timestamp=(
                            datetime.now(UTC) + timedelta(seconds=step * cfg.poll_seconds)
                        ).isoformat(),
                        **p.demo_sample(step),
                        source="demo",
                    ),
                )
        # Interrupted mutations are never replayed automatically.
        for item in p.store.list("actions"):
            if item["status"] == "executing":
                item.update(
                    status="failed", result="Process interrupted; verify cluster state before retry"
                )
                p.store.put("actions", item)
        await p.sample()
        p.audit("system", "startup", "platform", "ready", f"{cfg.mode} mode; healing paused")
        worker = asyncio.create_task(p.run())
        autonomous_worker = asyncio.create_task(p.autonomy.run())
        yield
        autonomous_worker.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await autonomous_worker
        worker.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await worker
        for ws in list(p.clients):
            await ws.close(code=1001)
        p.store.close()

    app = FastAPI(
        title="AutoHealOps API",
        version="2.0.0",
        lifespan=lifespan,
        description="CPU/memory fractions 0–1; latency milliseconds; restarts count over last 5 minutes in live mode. UTC ISO timestamps. Demo mode is simulated and never mutates Kubernetes.",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cfg.origins,
        allow_credentials=False,
        allow_methods=["GET", "POST", "PUT"],
        allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
    )
    attempts = defaultdict(deque)

    @app.middleware("http")
    async def request_context(request, call_next):
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        body = bytearray()
        async for chunk in request.stream():
            body.extend(chunk)
            if len(body) > 65536:
                return Response("Request too large", status_code=413)
        request._body = bytes(body)
        start = time.monotonic()
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        REQUESTS.labels(request.method, str(response.status_code)).inc()
        LATENCY.observe(time.monotonic() - start)
        log.info(
            '{"request_id":"%s","method":"%s","status":%s}',
            request_id,
            request.method,
            response.status_code,
        )
        return response

    @app.exception_handler(Exception)
    async def internal_error(request, exc):
        log.error(
            '{"request_id":"%s","error_type":"%s"}',
            getattr(request.state, "request_id", ""),
            type(exc).__name__,
        )
        return Response(
            '{"detail":"Service unavailable; use request ID to investigate"}',
            status_code=503,
            media_type="application/json",
        )

    def platform():
        return app.state.platform

    def identity(credentials: HTTPAuthorizationCredentials | None = Depends(security)):
        if cfg.mode == "demo" and cfg.environment == "development":
            return {"sub": "demo-operator", "role": "admin"}
        if not credentials:
            raise HTTPException(401, "Bearer token required")
        try:
            claims = jwt.decode(
                credentials.credentials,
                cfg.jwt_secret,
                algorithms=["HS256"],
                options={"require": ["exp", "sub", "role"]},
            )
            if claims["role"] not in ("admin", "viewer"):
                raise ValueError()
            return claims
        except Exception:
            raise HTTPException(401, "Invalid or expired token") from None

    def admin(actor=Depends(identity)):
        if actor["role"] != "admin":
            raise HTTPException(403, "Administrator role required")
        return actor

    @app.get("/health/live")
    @app.get("/")
    def live():
        return {
            "status": "ok",
            "version": "2.0.0",
            "mode": cfg.mode,
            "authentication_required": not (
                cfg.mode == "demo" and cfg.environment == "development"
            ),
        }

    @app.get("/health/ready")
    def ready():
        p = platform()
        try:
            p.store.ping()
        except Exception:
            raise HTTPException(503, "Persistence unavailable") from None
        if (
            not p.worker_updated
            or (datetime.now(UTC) - datetime.fromisoformat(p.worker_updated)).total_seconds()
            > cfg.poll_seconds * 4 + 30
        ):
            raise HTTPException(503, "Collector stale; inspect integration status")
        return {"status": "ready", "mode": cfg.mode, "integrations": p.integration}

    @app.get("/metrics", include_in_schema=False)
    @app.get("/telemetry")
    def telemetry():
        p = platform()
        worker = (
            1
            if p.worker_updated
            and (datetime.now(UTC) - datetime.fromisoformat(p.worker_updated)).total_seconds()
            < cfg.poll_seconds * 4 + 30
            else 0
        )
        extra = f"autohealops_worker_healthy {worker}\nautohealops_anomalies_retained {len(p.store.list('anomalies'))}\n"
        for status in ("simulated", "dry_run", "succeeded", "failed"):
            extra += f'autohealops_healing_actions{{status="{status}"}} {sum(x["status"] == status for x in p.store.list("actions"))}\n'
        return Response(generate_latest() + extra.encode(), media_type=CONTENT_TYPE_LATEST)

    @app.post("/auth/login", include_in_schema=False)
    @app.post("/api/v1/auth/login")
    def login(body: LoginInput, request: Request):
        key = request.client.host if request.client else "unknown"
        q = attempts[key]
        clock = time.monotonic()
        while q and q[0] < clock - 60:
            q.popleft()
        if len(q) >= 5:
            raise HTTPException(429, "Five login attempts per minute allowed")
        q.append(clock)
        # Bounded number of source buckets; proxy deployments must configure trusted forwarding.
        if len(attempts) > 1000:
            attempts.pop(next(iter(attempts)))
        password = (
            cfg.admin_password
            if body.username == "admin"
            else cfg.viewer_password
            if body.username == "viewer"
            else ""
        )
        if not password or not hmac.compare_digest(body.password, password):
            raise HTTPException(401, "Invalid credentials")
        return {
            "access_token": jwt.encode(
                {
                    "sub": body.username,
                    "role": "admin" if body.username == "admin" else "viewer",
                    "exp": datetime.now(UTC) + timedelta(hours=1),
                },
                cfg.jwt_secret,
                algorithm="HS256",
            ),
            "token_type": "bearer",
        }

    @app.get("/api/v1/overview", response_model=Overview)
    def overview(actor=Depends(identity)):
        return platform().overview()

    def listing(
        kind,
        limit,
        offset,
        q="",
        severity="",
        status="",
        component="",
        resource="",
        action="",
        since=None,
    ):
        rows = platform().store.list(kind)
        rows = [
            x
            for x in rows
            if (not q or q.lower() in str(x).lower())
            and (not severity or x.get("severity") == severity)
            and (not status or x.get("status") == status)
            and (not component or x.get("component") == component)
            and (not resource or resource.lower() in x.get("target", "").lower())
            and (not action or x.get("action") == action)
            and (since is None or datetime.fromisoformat(x["timestamp"]) >= since.astimezone(UTC))
        ]
        return {
            "items": rows[offset : offset + limit],
            "total": len(rows),
            "limit": limit,
            "offset": offset,
        }

    # All list capabilities share the same bounded pagination/filter contract.
    def list_endpoint(kind):
        def endpoint(
            limit: int = Query(50, ge=1, le=200),
            offset: int = Query(0, ge=0, le=1000),
            q: str = Query("", max_length=100),
            severity: str = "",
            status: str = "",
            component: str = "",
            resource: str = "",
            action: str = "",
            since: datetime | None = None,
            actor=Depends(identity),
        ):
            if since is not None and since.tzinfo is None:
                raise HTTPException(422, "since must include timezone")
            return listing(
                kind, limit, offset, q, severity, status, component, resource, action, since
            )

        return endpoint

    response_types = {
        "metrics": MetricRecord,
        "anomalies": AnomalyRecord,
        "alerts": AlertRecord,
        "actions": ActionRecord,
        "audit": AuditRecord,
    }
    for path, kind in [
        ("metrics", "metrics"),
        ("anomalies", "anomalies"),
        ("alerts", "alerts"),
        ("incidents", "alerts"),
        ("healing/actions", "actions"),
        ("audit/events", "audit"),
    ]:
        app.add_api_route(
            "/api/v1/" + path,
            list_endpoint(kind),
            methods=["GET"],
            name=kind + "_list",
            response_model=Page[response_types[kind]],
        )

    @app.get("/api/v1/clusters")
    def clusters(actor=Depends(identity)):
        p = platform()
        return {
            "items": [
                {
                    "id": "local",
                    "name": p.overview()["cluster"],
                    "source": cfg.mode,
                    "workloads": p.workloads,
                }
            ],
            "total": 1,
        }

    @app.get("/api/v1/predictions")
    async def predictions(actor=Depends(identity)):
        samples = list(reversed(platform().store.list("metrics")[:30]))
        if len(samples) < 6:
            return {
                "available": False,
                "reason": "At least six ordered samples required",
                "model": "linear-trend-baseline",
            }
        samples = [
            x
            for x in samples
            if all(
                x.get(k) is not None
                for k in ("cpu_usage", "memory_usage", "pod_restarts", "network_latency")
            )
        ]
        if len(samples) < 6:
            return {
                "available": False,
                "reason": "Incomplete telemetry; six complete ordered samples required",
                "model": "linear-trend-baseline",
            }
        sequence = [
            [x[k] for k in ("cpu_usage", "memory_usage", "pod_restarts", "network_latency")]
            for x in samples
        ]
        try:
            async with httpx.AsyncClient(verify=SSL_CONTEXT, trust_env=False, timeout=3) as client:
                response = await client.post(
                    f"{cfg.ai_url}/predict",
                    json={"sequence": sequence, "timestamps": [x["timestamp"] for x in samples]},
                )
                response.raise_for_status()
                return {
                    **response.json(),
                    "source": cfg.mode,
                    "data_freshness": samples[-1]["timestamp"],
                }
        except httpx.HTTPStatusError as exc:
            return {
                "available": False,
                "engine_available": True,
                "model": "linear-trend-baseline",
                "reason": "Forecast withheld: telemetry cadence or sequence failed validation"
                if exc.response.status_code == 422
                else f"AI service returned HTTP {exc.response.status_code}; forecast unavailable",
            }
        except Exception:
            return {
                "available": False,
                "model": "linear-trend-baseline",
                "reason": "AI engine unavailable; failure probabilities are not estimated",
            }

    @app.get("/api/v1/integrations/status")
    def integrations(actor=Depends(identity)):
        return {
            "mode": cfg.mode,
            "services": platform().integration,
            "storage": "mongodb" if cfg.mongo_uri else "sqlite",
            "notifications": platform().notifications.last,
            "model": "Inspect AI engine /model-status for training metadata",
        }

    @app.get("/api/v1/settings")
    def settings_view(actor=Depends(identity)):
        return platform().policy()

    @app.put("/api/v1/settings")
    def settings_update(body: PolicyInput, actor=Depends(admin)):
        if body.healing_mode == "automatic" and not cfg.allow_automatic:
            raise HTTPException(409, "Automatic mode requires startup ALLOW_AUTOMATIC=true")
        if body.healing_mode == "automatic" and cfg.mode == "live" and not cfg.automatic_targets:
            raise HTTPException(409, "Live automatic mode requires exact AUTOMATIC_TARGETS")
        p = platform()
        p.autonomy.streaks.clear()
        p.autonomy.evidence.clear()
        p.autonomy.last_sample.clear()
        p.paused = body.paused
        cfg.healing_mode = body.healing_mode
        p.audit(
            actor["sub"],
            "policy_changed",
            cfg.namespace,
            "updated",
            f"paused={body.paused}; mode={body.healing_mode}",
        )
        return p.policy()

    @app.post("/api/v1/demo/scenarios")
    async def scenario(body: ScenarioInput, actor=Depends(admin)):
        p = platform()
        if cfg.mode != "demo":
            raise HTTPException(409, "Scenario simulation is isolated to demo mode")
        async with p.lock:
            p.scenario = "healthy" if body.scenario == "reset" else body.scenario
            p.save_demo()
            if body.scenario == "reset":
                for alert in p.store.list("alerts"):
                    if alert["status"] != "resolved":
                        alert.update(status="resolved", resolved_at=now())
                        p.store.put("alerts", alert)
            await p.sample()
            p.audit(
                actor["sub"],
                "demo_scenario",
                cfg.namespace,
                body.scenario,
                "Explicit simulated fault; no real cluster mutation",
            )
        return p.overview()

    @app.post("/api/v1/healing/actions")
    def recommend(body: ActionInput, actor=Depends(admin)):
        return platform().recommend(body.model_dump(), actor["sub"])

    @app.post("/api/v1/healing/actions/{action_id}/approve")
    async def approve(action_id: str, body: DecisionInput, actor=Depends(admin)):
        p = platform()
        async with p.execution:
            item = p.store.get("actions", action_id)
            if not item:
                raise HTTPException(404, "Action not found")
            if item["status"] != "recommended":
                raise HTTPException(409, "Only recommendations can be approved")
            item.update(
                status="approved",
                approved_by=actor["sub"],
                approval_rationale=body.rationale,
                approved_at=now(),
            )
            p.store.put("actions", item)
            p.audit(
                actor["sub"],
                "approve",
                item["target"],
                "approved",
                body.rationale,
                item["correlation_id"],
            )
            return item

    @app.post("/api/v1/healing/actions/{action_id}/execute")
    async def execute(action_id: str, actor=Depends(admin)):
        return await platform().execute(action_id, actor["sub"])

    @app.post("/api/v1/alerts/{alert_id}/{decision}")
    def alert_action(alert_id: str, decision: str, actor=Depends(admin)):
        if decision not in ("acknowledge", "resolve"):
            raise HTTPException(404, "Unknown decision")
        p = platform()
        item = p.store.get("alerts", alert_id)
        if not item:
            raise HTTPException(404, "Alert not found")
        item.update(
            status="acknowledged" if decision == "acknowledge" else "resolved", updated_at=now()
        )
        p.store.put("alerts", item)
        p.audit(
            actor["sub"],
            decision,
            item["target"],
            item["status"],
            "Operator incident triage",
            item["correlation_id"],
        )
        return item

    @app.websocket("/ws")
    @app.websocket("/api/v1/ws")
    async def websocket(ws: WebSocket):
        if ws.headers.get("origin") not in cfg.origins:
            await ws.close(code=1008)
            return
        await ws.accept()
        p = platform()
        try:
            if not (cfg.mode == "demo" and cfg.environment == "development"):
                message = await asyncio.wait_for(ws.receive_json(), 5)
                identity(
                    HTTPAuthorizationCredentials(
                        scheme="Bearer", credentials=message.get("token", "")
                    )
                )
                # Clients reauthenticate on reconnect before token expiry.
                token_claims = jwt.decode(message["token"], cfg.jwt_secret, algorithms=["HS256"])
                expiry = token_claims["exp"]
            else:
                expiry = time.time() + 3600
            if len(p.clients) >= 100:
                await ws.close(code=1013)
                return
            p.clients.add(ws)
            await ws.send_json(
                {"type": "operational_update", "timestamp": now(), "overview": p.overview()}
            )
            while time.time() < expiry:
                try:
                    await asyncio.wait_for(
                        ws.receive_text(), timeout=min(30, max(0.1, expiry - time.time()))
                    )
                except TimeoutError:
                    continue
            await ws.close(code=1008)
        except (TimeoutError, WebSocketDisconnect, HTTPException, ValueError, jwt.PyJWTError):
            with contextlib.suppress(Exception):
                await ws.close(code=1008)
        finally:
            p.clients.discard(ws)

    # Legacy reads remain safe; the former unauthenticated mutation route is retired.
    app.add_api_route("/alerts/", list_endpoint("alerts"), methods=["GET"], include_in_schema=False)
    app.add_api_route(
        "/heal/logs", list_endpoint("actions"), methods=["GET"], include_in_schema=False
    )
    app.add_api_route(
        "/metrics/history", list_endpoint("metrics"), methods=["GET"], include_in_schema=False
    )
    return app


app = create_app()
