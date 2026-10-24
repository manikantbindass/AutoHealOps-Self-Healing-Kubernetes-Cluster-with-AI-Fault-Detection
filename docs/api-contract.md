# Request and response contracts

Base path `/api/v1`. JSON errors use `detail`; each HTTP response includes a generated `X-Request-ID`. Operational records have string `id`, UTC ISO-8601 `timestamp` and a workflow `correlation_id` where applicable. Public endpoints: `/health/live`, `/health/ready`, `/telemetry`, and login. The developer demo permits an explicitly named demo-operator; live/production requires bearer JWT. Viewer tokens can read; administrator tokens can mutate. Login is limited to five attempts per source per minute. TLS termination is required outside localhost.

Lists (`metrics`, `anomalies`, `alerts`, `incidents`, `healing/actions`, `audit/events`) return `{items,total,limit,offset}`. `limit` 1–200, `offset` 0–1000. Filters: `q`, `severity`, `status`, `component`, `resource`, `action`, `since` (timezone-aware ISO timestamp). Results inspect the latest 1,000 retained records per collection; total is the matching count within that bounded window. UI shows up to 200. Incidents share the alert lifecycle, not a separate ticketing system.

- `GET overview`: provenance, current metrics or null, inventory counts, pod phase counts, active alerts, recent actions/events, integration health, current policy.
- `GET clusters`: single configured authorization boundary and available workload inventory. Cluster-wide nodes are unavailable in live namespace-scoped mode.
- `GET predictions`: chronological one-step CPU/memory forecast or `{available:false,reason}`. Never a calibrated failure probability.
- `GET integrations/status`, `GET settings`: safe status/configuration; secret values and destination URLs are excluded.
- `PUT settings`: `{paused:boolean,healing_mode:recommendation|manual|automatic}`. Automatic requires startup authorization. Restart always resets pause; runtime policy edits are audited, not persisted.
- `POST demo/scenarios`: `{scenario:cpu|memory|restarts|latency|reset}`. Rejected in live mode. Scenario persists on restart; reset resolves demo alerts and restores healthy telemetry while preserving history.
- `POST healing/actions`: `{action:restart_deployment|scale_deployment,namespace,target,replicas?,rationale}`. Only explicitly managed deployments are eligible. Duplicate pending requests reuse the same action.
- `POST healing/actions/{id}/approve`: `{rationale}`; records actor identity.
- `POST healing/actions/{id}/execute`: executes approved action subject to pause, mode, ownership, limits, cooldown and one-attempt budget. Replays of completed actions return the prior result. All scaling requires approval even in automatic mode. Automatic mode may execute rollout-restart recommendations; live aggregate detections never automatically select a target.
- `POST alerts/{id}/acknowledge` or `/resolve`: operator triage with audit history. Simulated recovery does not silently resolve an incident.

WebSocket `/api/v1/ws` (`/ws` alias): same allowed Origin list as CORS; live/production sends `{token:JWT}` as first message within 5 seconds, never in URL. Emits `{type:"operational_update",timestamp,overview}`. One collector per process broadcasts actual state, not one loop per client. Client reconnect backs off 1–30 seconds and closes on unmount. Token expiry closes the connection. REST fallback refreshes every 15 seconds without overlapping requests. Maximum 100 clients; slow client sends time out after 1 second. Browser errors remain visible; no invented fallback measurements.

Feature ordering: CPU fraction [0,1], memory fraction [0,1], integer restart count [0,100000], network latency milliseconds [0,60000]. Live restarts represent 5-minute increase, rounded to a count; demo uses an explicit sample count. Missing live exporters yield null values while preserving available features, never zero or demo substitution. Error rate is not exposed because an application-level request/error counter is not universally available. AI endpoints and training metadata are documented in `ai-models.md`.

Legacy login, `/alerts/`, `/heal/logs`, `/metrics/history` and `/ws` remain. `/metrics` now exports Prometheus instrumentation (alias `/telemetry`); obsolete unauthenticated `POST /heal` is removed. This is an intentional security migration.

Automatic unapproved execution is restricted to detector-originated demo recommendations. Live actions and operator-created recommendations require explicit approval because live aggregate telemetry does not provide workload-level attribution.
