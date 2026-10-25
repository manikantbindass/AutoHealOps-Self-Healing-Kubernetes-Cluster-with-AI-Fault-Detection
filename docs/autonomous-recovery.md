# Autonomous recovery

AutoHealOps can detect a supported workload condition, choose a configured runbook, execute it without a per-action approval, verify the outcome and record the result. An administrator must first opt in the workload and resume automatic mode. This is bounded autonomy for two runbooks, not a promise to diagnose or repair every Kubernetes failure.

## What happens automatically

| Mode | Automatic behavior |
| --- | --- |
| Public browser simulation | Select **Autonomous recovery** in Settings, save, then **Resume healing** in Healing operations. Inject a fault. After three samples, the browser simulates recovery without approval and resolves the related incident. No cluster, backend or trained ML service is connected. |
| Local backend demo | `ALLOW_AUTOMATIC=true`, automatic policy and runtime resume enable detector-generated simulated rollout restarts. No real mutation occurs. |
| Configured live namespace | Exact opted-in Deployments receive workload-specific checks. Three distinct fresh source samples confirm a runbook before execution. Dry-run remains the default; real mutations require `DRY_RUN=false`. |

### Live runbooks

1. **Repeated restarts:** more than five container restarts across the owned Pods in a one-minute window proposes a Deployment rollout restart.
2. **CPU pressure:** maximum owned-container CPU usage above 80% of its limit proposes one additional replica, up to `MAX_REPLICAS` (default five). Restart conditions take precedence.

Memory and latency still support monitoring and investigation. They do not independently select a live autonomous repair. The runbooks use explicit rules; the separate trained anomaly detector does not diagnose the correct repair or predict exact failure times. Scaling cannot fix every CPU problem, and restarting cannot fix a bad image or configuration. Failed verification pauses healing for investigation.

## Attribution and evidence

The adapter follows Deployment UID → controller ReplicaSet UID → controller Pod UID references. Name prefixes and namespace averages do not choose the target. Pod names become exact entries in the Prometheus query scope. The controller checks CPU, memory and restart measurements, resource limits, coverage of every owned active Pod and source scrape age (at most 60 seconds). Missing, ambiguous, non-finite, stale or incomplete evidence blocks automation and resets confirmation.

Confirmation requires distinct source samples with stable Deployment UID, generation and owned Pod names. Re-reading the same scrape does not count again. Namespace-wide dashboard detections remain separate: they open alerts and never authorize a target.

## Enable in a deliberate test namespace

Use a single backend worker/replica with MongoDB, a reachable Prometheus, kube-state-metrics and kubelet/cAdvisor collection. All target containers need CPU and memory limits. Use scoped identity, strong application credentials and the namespace Role in `k8s/rbac.yaml`. It now also reads ReplicaSets and HPAs. Do not grant deletion or cluster-admin rights.

Set these backend environment values using your existing deployment tooling:

```dotenv
MODE=live
ENVIRONMENT=production
ALLOW_AUTOMATIC=true
HEALING_MODE=automatic
AUTOMATIC_TARGETS=checkout-service
AUTOMATIC_CONFIRMATIONS=3
AUTOMATIC_VERIFY_SECONDS=120
DRY_RUN=true
NAMESPACE=autohealops
MAX_REPLICAS=5
COOLDOWN_SECONDS=300
```

Supply `MONGO_URI`, `JWT_SECRET`, `ADMIN_PASSWORD`, explicit `ORIGINS` and `PROMETHEUS_URL` through appropriate secret/configuration tooling. `AUTOMATIC_TARGETS` is a comma-separated list of at most 20 exact Deployment names, not a wildcard. The namespace must have **no HPAs**: this conservative first implementation blocks automation if any HPA exists there. The optional `k8s/autoscaler.yaml` example therefore must not be applied in an autonomous target namespace.

On each reviewed target Deployment set both metadata labels:

```yaml
autohealops.io/managed: "true"
autohealops.io/autonomous: "true"
```

Do not label the AutoHealOps control plane itself. Paused and zero-replica Deployments are ineligible. Start with dry-run; inspect the generated action, exact evidence and audit. When workload-specific testing justifies real changes, set `DRY_RUN=false` and restart the backend. Startup always pauses healing; explicitly resume it in the UI. Selecting automatic policy alone does not resume it.

## Execution, verification and stopping

Immediately before mutation the adapter rechecks namespace, both labels, UID, generation, paused state, replicas and HPA absence. A resource-version precondition rejects intervening Deployment changes. The existing shared execution lock, one attempt per action, target cooldown and ten-actions-per-hour budget apply to autonomous and manual actions together.

The adapter first checks rollout availability (observed generation, updated and available replicas; 45-second polling window and five-second API request timeouts). The controller then waits for **two distinct healthy source observations**: CPU at or below 80%, memory at or below 85%, and no more than five restarts in the one-minute window. Verification has a configurable 120-second polling window, plus bounded in-flight API calls. Only then is the action `succeeded`, with `telemetry_verified=true`, and its correlated incident resolved. These checks do not prove that every customer request is healthy.

Dry-run records `dry_run` and makes no Kubernetes mutation or claim of recovered telemetry. Any autonomous execution/verification failure records `failed`, leaves the incident open and pauses healing. A persisted per-target latch prevents another autonomous attempt for the same sustained fault. Two healthy source observations clear the latch; records follow the configured retention period. An operator may investigate and create a separate approved action when needed.

Emergency pause prevents new operations. A Kubernetes mutation already accepted cannot be undone by pause. Verification stops when policy is paused. Every process restart begins paused and marks interrupted actions failed rather than replaying them. Confirmation counters restart from zero. Repeated requests for completed actions return the recorded result.

## Verification status and boundaries

A separate autonomous task lets normal collection and dashboard updates continue while recovery verification waits.

The automated contract suite exercises confirmation, dry-run, rollout/telemetry outcomes, circuit pause, missing/stale data, authorization changes and public automatic simulation. It uses controlled adapters and HTTP responses. This development environment has no configured Kubernetes context and no running Docker engine, so these results do **not** establish real-cluster or production acceptance.

Before real use, verify the actual Prometheus labels, scrape cadence, resource limits, RBAC, UID ownership, rollout conditions and workload health in a disposable namespace. Exercise a successful scale/restart, insufficient telemetry, revoked labels, HPA conflict, rollout failure, persistently unhealthy measurements, pause during recovery and process restart. Retain the cluster evidence separately. Multi-cluster control, distributed workers, arbitrary repair scripts, volume/database deletion and automatic rollback are outside this implementation.

References: [Kubernetes Deployments](https://kubernetes.io/docs/concepts/workloads/controllers/deployment/) and [Prometheus query functions](https://prometheus.io/docs/prometheus/latest/querying/functions/). These explain upstream semantics; the repository tests establish only the contracts they exercise.
