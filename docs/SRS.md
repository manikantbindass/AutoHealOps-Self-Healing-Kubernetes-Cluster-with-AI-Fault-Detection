# AutoHealOps 2.0 requirements and scope

Author: Manikant Kumar. This document distinguishes delivered behavior from production goals; it does not assert uptime, model accuracy or automatic repair latency without evidence.

## Delivered functional scope

1. Eight responsive React views: overview, inventory/detail inspection, telemetry, fault intelligence, safe recovery, incidents, audit, settings/integration status.
2. Explicit deterministic demo mode with healthy workloads and CPU/memory/restart/latency scenarios. No demo operation invokes Kubernetes.
3. FastAPI v1 contracts, bounded pagination/retention, request IDs, UTC timestamps, validated feature inputs and OpenAPI documentation.
4. SQLite native persistence or MongoDB document persistence/indexes, bounded startup retries, liveness/readiness and application Prometheus instrumentation.
5. One shared collector broadcasts changing operational snapshots; browser reconnects exponentially and uses a bounded fallback refresh.
6. Compatible persisted StandardScaler/IsolationForest inference, explicit CLI training and transparent threshold fallback. Forecasting compares trend/persistence using chronological holdout. No calibrated failure probability is claimed.
7. Recommended/approved/executing/completed remediation with explicit dry-run, pause, one operation concurrency, namespace/ownership validation, replica cap, cooldown, hourly budget, deduplication and idempotent completion.
8. Live rollout restart/scale adapters verify rollout availability, failing honestly when unavailable/unverified. No namespace, volume, database, node drain or arbitrary shell operations.
9. Strong live/production credentials, expiring JWTs, administrator/viewer roles, CORS/WS origin checks, login throttling and secret-free settings responses.
10. Optional validated Slack and STARTTLS email adapters; delivery is best effort and visible through integration status. Defaults require no external account.
11. Local Compose and native setup paths; separate least-privilege Kubernetes examples; CI for tests/build/configuration/container checks.

## Acceptance evidence

Use `docs/validation.md`, automated tests and real screenshots. Synthetic model metrics are not real-world validation. A parsed manifest is not a deployed cluster. An accepted rollout is not proof of restored application metrics. A simulation is never a real repair.

## Planned enterprise scope

Distributed control-plane locks/leases, multi-cluster authorization, durable background queues/event broker, SSO, calibrated failure prediction, immutable external audit retention, a durable notification outbox, production load/chaos testing, and automated backup orchestration remain future work. Backend horizontal scaling is intentionally unsupported in this single-process release.
