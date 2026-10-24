# Validation record — 2026-10-24

Observed in the Windows workspace on `feature/autohealops-2.0`, based on clean `main` at `62db65d`.

| Check | Actual result |
|---|---|
| Backend pytest | 19 passed: contracts, feature boundaries, auth/roles/rate limit, persistence/retention, WebSocket, approvals, cooldown, dry-run, failure, ownership, safe automatic policy, partial exporter data and forecast validation/outage distinction |
| AI pytest | 12 passed: invalid inputs, deterministic training/scaler persistence, temporal evaluation, missing/corrupt artifacts, hybrid threshold guard |
| Frontend Vitest | 6 passed: empty incidents, acknowledgement, approval, resource details, truthful forecast state, reconnect/backoff/cleanup |
| Production build | Vite build passed; compiled static bundle served by the native preview |
| Lint and formatting | ESLint, Prettier, Ruff checks passed; Python compileall passed |
| Native health | Dashboard 13000, API ready/live 18000, AI 18001 all responded successfully |
| Browser integration | Real Edge + Playwright passed 8 routes, live WebSocket, synthetic CPU fault, approval, simulated recovery, details/Escape, 390px mobile width and no page JavaScript errors |
| Screenshots | Five genuine screenshots from the running compiled app; dashboard and gallery paths verified |
| Compose | `docker compose config --quiet` passed; no Docker engine was available for image builds/runtime |
| Kubernetes static consistency | 16 objects checked for namespace/RBAC/probes/resources/image versions; no server admission/runtime claim |
| Monitoring static consistency | Six Grafana panels and actual platform scrape/provisioning paths checked; monitoring containers not launched |
| npm audit | 0 known findings after Vite/Vitest migration and patched React Router |
| Python installed-environment audit | 0 known findings across 88 packages after Kubernetes 37.0.1 / urllib3 2.8.0 upgrade |

The inherited CRA audit initially found 58 npm findings. The build/test toolchain was replaced while preserving React, Axios, Router, Recharts and Lucide. Router was upgraded to the patched major with navigation/component/browser regressions passing. Runtime Python direct dependencies are pinned to tested versions; development tools live in separate requirements. Audits are point-in-time checks, not a guarantee against future advisories.

The browser test exposed an actual single-feature detection gap: Isolation Forest alone did not flag CPU=0.96 while other features were normal. The fix uses an explicitly labelled hybrid threshold guard, retains the unchanged model decision/score, and adds a focused regression. It never claims the model caught a fault that only the threshold rule detected. Repeated browser runs respect the configured cooldown instead of disabling safeguards.

Synthetic Isolation Forest evaluation: precision 0.8772, recall 1.0, F1 0.9346 on independent synthetic held-out rows. These are model-only synthetic metrics and do not establish production accuracy. Forecasting reports chronological baseline errors, not failure probabilities.

## Environmental limitations

Docker's Windows/Linux engine pipes were unavailable, and no real cluster was used. Docker image builds, Compose runtime, live MongoDB, Grafana/Prometheus runtime, actual Kubernetes mutation, HPA, NetworkPolicy enforcement, TLS ingress and external Slack/email delivery are unverified here. CI includes builds and a browser job, but remote CI results must be reviewed after pushing.

Initial sandboxed test attempts failed on Windows temporary-directory/socket permissions. Successful tests used workspace-local temporary files and an approved normal process context. A Windows WMI diagnostic appeared on one intermediate NumPy import; the final AI rerun passed without that diagnostic. The requirements-resolving Python auditor stalled; the installed environment was successfully audited instead. Starlette currently emits a TestClient/httpx deprecation warning; tests pass, and this is not a failure.

The application is a single-process control plane, not production HA. Multi-cluster authorization, durable distributed execution/notifications, calibrated failure prediction and production load/recovery verification remain future work. See `environment-blockers.md` and `security-operations.md`.

## Public Vercel deployment follow-up

PR #1 merged after all checks passed; the original dashboard screenshot is verified on main. The public deployment is READY at https://autohealops.vercel.app. The repository About website points to that URL.

- Ten frontend tests passed (six original UI tests plus four public-demo behavior tests); lint/formatting, normal build and isolated showcase build passed.
- Real unauthenticated Edge/Playwright against the Vercel URL passed provenance, browser rules, fault/approval/recovery, all routes/direct deep links, session history, mobile width, zero API/WebSocket traffic, and zero page JavaScript errors.
- `docs/screenshots/autohealops-vercel.png` is a genuine, visually inspected screenshot captured from the deployed URL. Original README animation markup is preserved.
- Vercel hosts only an explicitly labelled per-browser simulation. FastAPI, persistent databases, trained ML, shared event delivery and actual Kubernetes execution still require the normal backend deployment.
