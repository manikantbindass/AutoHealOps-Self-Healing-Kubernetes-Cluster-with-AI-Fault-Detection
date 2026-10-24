# AutoHealOps 2.0 implementation plan

Baseline: main at 62db65d; clean checkout cloned into an empty workspace. No existing tests or lockfile. React 18/CRA, FastAPI, Motor/Mongo, Isolation Forest and optional TensorFlow are present.

## Audit findings
- Metrics silently become random when Prometheus fails; frontend independently invents data.
- Auth has a known default password/signing key and does not protect operational routes.
- Healing deletes pods across a namespace, lacks approval, cooldown, ownership checks and outcome verification.
- Mongo startup does not ping, provision indexes, or close. BSON IDs cannot safely serialize.
- WebSocket broadcasts timestamps from each client loop, not changing operational data.
- Predictor presents heuristic values as calibrated probability and time-to-failure.
- Compose mounts host kubeconfig, uses latest tags, lacks health checks and Grafana provisioning.
- No tests, CI, genuine screenshots, retention policy, or dependable setup scripts exist.

## Delivery order
1. Preserve React/FastAPI stack; introduce validated settings, persistent SQLite demo / optional Mongo live storage, versioned APIs, authorization and a single event collector.
2. Implement deterministic demo scenarios, auditable dry-run/manual policy, bounded execution and namespace-scoped Kubernetes adapters.
3. Validate feature inputs; train/persist scaled Isolation Forest explicitly; replace unsupported probability claims with a temporal metric-forecast baseline.
4. Build eight responsive operational views using existing React Router/Recharts/Lucide/Axios dependencies. Surface data provenance and integration errors.
5. Repair Compose, Dockerfiles, Kubernetes examples, monitoring and Windows scripts. Document operational boundaries.
6. Run automated tests/build/config checks, native integration and real browser screenshot; review, commit, push feature branch, open PR.

## Constraints
Docker CLI exists but engine is currently unavailable. Native Python 3.14 and Node 24 are installed. Docker builds and a real Kubernetes repair require those services; distinguish configuration validation from runtime verification. Single-process demo is intentional; distributed coordination/multi-cluster authorization remain future work.

## Implementation adjustment
The actual frontend audit found 58 findings in the inherited CRA dependency tree. Preserve React/Router/Axios/Recharts/Lucide, replace only CRA build/test tooling with Vite/Vitest, add explicit ESLint/Prettier, and rerun build/tests/browser verification. This is a security and maintainability change, not a rewrite of the application stack.
