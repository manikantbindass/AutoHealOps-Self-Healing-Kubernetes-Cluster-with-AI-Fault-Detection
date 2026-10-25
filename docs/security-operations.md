# Security and operations

Live/production startup rejects missing/short signing keys and administrator passwords. The developer demo has no login by design, explicitly labels its identity, binds to localhost in documented workflows and never invokes Kubernetes. Do not expose developer mode publicly. JWTs expire after one hour; roles gate reads versus mutations. Use TLS and central identity/secrets management before real deployment. The bundled API docs and platform scrape are public within the trusted deployment boundary; protect them at ingress if exposing the service.

Secrets belong in `.env` (ignored), your deployment environment or Kubernetes Secret references. Settings and integration APIs return availability/status only. The application logs request ID/method/status and exception class without request bodies, bearer headers, database URI or webhook URL. HTTP client INFO logging is disabled in the backend to avoid printing secret webhook paths. Audit stores operator rationales; do not enter secrets in rationale fields.

Slack webhook validation permits only HTTPS hooks.slack.com/services paths with no embedded credentials or alternate ports; redirects are not followed. SMTP uses mandatory STARTTLS with certificate verification and timeouts. Notification attempts are best effort with no durable queue/retry guarantee. This repository does not send anything by default.

The Kubernetes Role has no delete verbs or cluster-wide grants. Runtime rechecks namespace and the opt-in Deployment label. RBAC grants patch capability within the namespace, so a compromised backend identity remains powerful there; isolate a test namespace and strengthen admission controls for production. Avoid the former host kubeconfig mount. Real pod deletion/rescheduling is intentionally excluded. Dry-run does policy validation only; it does not claim Kubernetes server-side admission validation.

Docker images run application processes as non-root; Compose uses no-new-privileges for app services. Local MongoDB intentionally has no authentication and no published port; treat the Compose network as a developer trust boundary. Production needs authenticated MongoDB with TLS, restricted egress and tested backups. Pinned service version tags improve reproducibility; image digests and a registry provenance policy should be added for controlled releases. Python dependencies are compatible bounded ranges; frontend has an npm lockfile. The inherited CRA toolchain was replaced with Vite/Vitest after dependency auditing; see validation.md for remaining findings. Do not advertise zero vulnerabilities without a current audit.

## Backup and restore

Native demo: stop the recorded native processes, copy `data/autohealops.sqlite` to private backup storage, then restart. To restore, stop the app, preserve the current DB, replace the database with the backup, and restart. Do not copy SQLite WAL state while writes are ongoing unless using SQLite's backup API. No database files are committed.

MongoDB: take a consistent `mongodump` from a privileged maintenance environment, encrypt and restrict the archive, test restore into a separate database, and use `mongorestore` only during a deliberate maintenance window. The bundled stack does not automate backup scheduling or guarantee recovery objectives. Preserve Grafana/Prometheus volumes if desired; the provisioned dashboard can be rebuilt from Git. Treat audit retention and backup retention as separate policies.

## Recovery and scaling

Readiness checks storage and collector freshness; optional exporter/AI failures remain visible as degraded integrations. Mongo startup retries are bounded; operation failures return a 503 with request ID instead of silently dropping records. The API process owns collection, in-memory pause and action execution. Keep one backend worker and one backend replica. On restart healing pauses and interrupted actions become failed, requiring operator investigation. Production HA requires durable action claims, a distributed lease and shared event delivery before adding replicas.

Rate limits, cooldown and locks protect one process only. No high-availability, production-load, disaster-recovery, external-notification or real-cluster validation was performed in this local environment. A passing synthetic test cannot establish production reliability.

## Autonomous policy

Automatic live actions require exact startup targets, both Deployment opt-in labels, workload-attributed fresh evidence and repeated confirmation. UID/generation/resource-version checks protect against changing targets. A failed verification pauses healing; a persisted per-target latch prevents repeated attempts for the sustained fault. No HPA may exist in an autonomous namespace. Manual requests still require approval. Removing `autohealops.io/autonomous=true` revokes live autonomous eligibility. See [runbooks and operator procedure](autonomous-recovery.md).
