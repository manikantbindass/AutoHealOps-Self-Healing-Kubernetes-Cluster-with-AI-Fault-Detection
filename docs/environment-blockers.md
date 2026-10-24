# Environment and infrastructure blockers

- Docker Desktop CLI is installed but both Windows and Linux engine named pipes were unavailable. `docker compose config --quiet` can run without the daemon; container builds and runtime cannot.
- No functioning Kubernetes cluster was used. Manifests are statically checked only. Server admission, RBAC enforcement, HPA, ingress TLS and real healing need a deliberately configured local cluster.
- Default TCP 3000/8000 were unavailable. Native execution supports explicit alternate ports and checks them before startup.
- Windows sandbox denies some local sockets and temporary-directory operations. Native health/browser checks ran in an approved normal process context; no unrelated processes were stopped.
- Playwright's managed Chromium was absent; the installed Edge browser was used for real screenshots. E2E supports either browser.
- No Slack/SMTP credentials were provided; validation and failure handling can be tested without sending messages.
- Live MongoDB, Grafana and Prometheus runtime require the Docker engine or independently running services. Native demo uses persistent SQLite and synthetic telemetry explicitly.

Remaining deployment commands once Docker Desktop is running in Linux-container mode:

```powershell
./scripts/setup.ps1
./scripts/start-local.ps1 -Monitoring
docker compose ps
./scripts/health-check.ps1
```

GitHub delivery is attempted using the existing authenticated account; see final report for actual push/PR results.
