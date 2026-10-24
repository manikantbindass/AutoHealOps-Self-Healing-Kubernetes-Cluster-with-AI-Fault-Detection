# Setup guide

## Docker Compose on Windows (primary distribution)

Install Docker Desktop with Linux containers and Docker Compose v2. Git is needed only to clone. Budget approximately 4–6 GB RAM for the core stack; adding monitoring increases this. Model build and image downloads require internet access.

```powershell
git clone https://github.com/manikantbindass/AutoHealOps-Self-Healing-Kubernetes-Cluster-with-AI-Fault-Detection.git
cd AutoHealOps-Self-Healing-Kubernetes-Cluster-with-AI-Fault-Detection
git switch feature/autohealops-2.0
./scripts/setup.ps1
# Optional monitoring profile:
./scripts/start-local.ps1 -Monitoring
./scripts/run-demo.ps1 -Scenario cpu
./scripts/health-check.ps1
./scripts/stop-local.ps1
```

Setup preserves an existing `.env`, creates it only when absent, fills only blank credential fields with cryptographic random values, validates Compose quietly, builds, waits for health and prints actual URLs. It never prints credentials. Grafana credentials remain private in `.env`. When PowerShell execution policy blocks scripts, invoke an individual script with `powershell -NoProfile -ExecutionPolicy Bypass -File ./scripts/setup.ps1` if permitted by your organization's policy.

The minimal core can also start with `Copy-Item .env.example .env` followed by `docker compose up --build -d --wait --wait-timeout 240`. This is explicitly an isolated developer demo with no external credentials. Generate a strong Grafana password before enabling the monitoring profile. All public ports bind loopback; MongoDB is internal. No host kubeconfig is mounted.

Linux/macOS: `bash scripts/setup.sh`; optional `docker compose --profile monitoring up --build -d --wait`. `stop-local.ps1`/`docker compose down` preserve volumes. Removing volumes is an intentional data deletion operation; do not use `down -v` unless you want to erase state.

| Service | Default URL | Availability |
|---|---|---|
| Dashboard | http://localhost:3000 | core |
| API docs | http://localhost:8000/docs | core |
| API ready/live | http://localhost:8000/health/ready | core |
| AI docs/model status | http://localhost:8001/docs /model-status | core |
| Platform scrape | http://localhost:8000/telemetry | core |
| Prometheus | http://localhost:9090 | monitoring profile |
| Grafana | http://localhost:3001 | monitoring profile |

## Native Windows fallback (verified on this machine)

Python 3.12, Node 22+ and npm are required. Docker/MongoDB/Kubernetes are optional in this path. The startup script builds a workspace virtual environment, installs dependencies, compiles React and launches hidden processes. It does not load `.env` secrets; it explicitly forces a safe developer demo using SQLite. Use Compose or deliberate environment setup for live mode.

```powershell
./scripts/start-native.ps1 -Install
./scripts/stop-native.ps1
```

On this machine ports 3000/8000 were unavailable. The verified invocation uses:

```powershell
./scripts/start-native.ps1 -BackendPort 18000 -AiPort 18001 -DashboardPort 13000
./scripts/run-demo.ps1 -Scenario cpu -BackendPort 18000 -DashboardPort 13000
./scripts/health-check.ps1 -BackendPort 18000 -AiPort 18001 -DashboardPort 13000
# Dashboard http://localhost:13000
# API http://localhost:18000/docs ; AI http://localhost:18001/docs
```

For a fresh install with alternate ports, add `-Install` to that command. Startup refuses occupied or reserved ports before launching any service. Logs and recorded process IDs are in ignored `.local/`. Stop only the recorded process trees with `stop-native.ps1`; for an old session verify that the process IDs have not been reused first. The preview server is a local verification tool for the compiled bundle. Docker uses unprivileged nginx.

Manual equivalent in separate terminals: create `.venv` with Python 3.12, install both requirements files, run `uvicorn main:app --host 127.0.0.1 --port 8001` in `ai-engine/` and the same on port 8000 in `backend/`. Set `AI_URL` and `ORIGINS` if changing ports. Run `npm ci` and `npm run build` in `frontend/`; run `node scripts/serve-preview.cjs` from root. The preview reads `BACKEND_PORT` and `DASHBOARD_PORT`, defaulting to 8000/3000. Native model training is optional: from `ai-engine`, run `../.venv/Scripts/python.exe -m training.train_anomaly`, then restart AI. Until then, status accurately labels rules.

## Demo workflow

The UI banner labels all demo data. Use Scenario lab on Overview or `run-demo.ps1` to inject CPU/memory/restart/latency faults. Open AI fault intelligence to inspect evidence, then Healing operations. Enter a rationale, approve the recommendation, resume healing, and select Simulate recovery. The record contains before/after metrics and an explicitly simulated result. Review/resolve the associated incident. Emergency pause blocks new executions. Reset scenario restores healthy telemetry and resolves demo incidents while preserving audit/history.

## Optional local Kubernetes

The manifests default to a single-instance, dry-run, paused demonstration in namespace `autohealops`. They do not create an external production cluster. Install Minikube or another local cluster, a default storage provisioner and at least 4–6 GB RAM. Build and load local images:

```powershell
minikube start --memory=6144 --cpus=4
docker build -t autohealops-backend:2.0.0 backend
docker build -t autohealops-ai-engine:2.0.0 ai-engine
docker build -t autohealops-frontend:2.0.0 frontend
minikube image load autohealops-backend:2.0.0
minikube image load autohealops-ai-engine:2.0.0
minikube image load autohealops-frontend:2.0.0
kubectl apply -f k8s/config.yaml
kubectl apply -f k8s/rbac.yaml
kubectl apply -f k8s/services.yaml
kubectl apply -f k8s/deployments.yaml
kubectl apply -f k8s/network-policy.yaml
kubectl -n autohealops rollout status deployment/autohealops-backend
kubectl -n autohealops port-forward service/frontend 3000:3000
```

HPA is frontend-only, optional, and requires `minikube addons enable metrics-server` before applying `k8s/autoscaler.yaml`. Backend must remain one replica/worker. NetworkPolicy ingress allows same-namespace traffic and frontend TCP/3000; enforcement requires a compatible CNI. Ingress is separate under `k8s/optional/`; configure ingress-nginx, local DNS/hosts and a TLS Secret `autohealops-tls` before applying. Set `ORIGINS=https://autohealops.local` when using that origin. No certificate or TLS success is implied by including the example.

For live monitoring, provide a reachable authenticated MongoDB and a Prometheus installation with kube-state-metrics, kubelet/cAdvisor and request histogram metrics. Set ConfigMap `MODE=live`, `ENVIRONMENT=production`, and add Kubernetes `secretKeyRef` environment entries for `JWT_SECRET`, `ADMIN_PASSWORD`, optional `VIEWER_PASSWORD`, and `MONGO_URI` to backend. Generate secrets through your local secret tooling; never commit a Secret containing credentials. The service account has namespace-scoped read/patch access only, with no deletion verbs. Mark only a deliberate demo target Deployment with `autohealops.io/managed=true`. Runtime code rechecks the label before mutation; namespace RBAC alone cannot enforce label authorization. Keep `DRY_RUN=true` until the exact target and identity have been reviewed. Switching to real mutations requires explicit `DRY_RUN=false`; automatic mode additionally requires `ALLOW_AUTOMATIC=true` and runtime resume. Never mount an administrator kubeconfig in Compose.

## Troubleshooting and verification limits

- Docker pipe/daemon error: start Docker Desktop, choose Linux containers, then `docker info`. This machine had no running Docker engine, so Compose configuration was verified but image builds and container runtime were not.
- Port reserved or occupied: use the native alternate-port flags; inspect the owning process rather than terminating unrelated applications.
- Startup timeout: inspect `.local/*error.log` for native mode, or `docker compose ps` and `docker compose logs --tail 100`. Do not share logs containing destination configuration.
- Database outage: readiness returns 503; Mongo startup retries five times. Driver reconnects after transient interruptions; no silent in-memory persistence is substituted.
- Missing live metrics: install/configure exporters and resource limits. Available measurements remain visible; missing ones show as gaps. No metrics are fabricated when an exporter or Prometheus is absent.
- Missing model: use the documented training CLI, then restart AI. Rules remain explicitly labelled.
- Browser auth expires: sign in again. Tokens live only in sessionStorage and expire after one hour. Viewer credentials cannot approve or execute actions.
- Cooldown: wait the configured period or choose a different deliberate target; do not loop recommendations to bypass policy.
- Native package installation can require network access. Windows sandbox restrictions on temp directories may require `pytest --basetemp=data/test-backend` or running in a normal user terminal.

Container builds, live Mongo/Kubernetes/Grafana runtime and actual notification delivery must be tested on a machine with those optional services. See `validation.md` for measured results rather than assuming all deployment profiles were executed.
