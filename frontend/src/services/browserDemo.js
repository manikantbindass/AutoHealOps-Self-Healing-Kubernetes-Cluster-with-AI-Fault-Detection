/** Explicit, opt-in public showcase. No network, ML, credentials or cluster access. */
const KEY = "autohealops-public-demo-v1";
const namespace = "autohealops";
const clock = () => new Date().toISOString();
const id = () => crypto.randomUUID();
const clone = (value) => JSON.parse(JSON.stringify(value));
const policyDefaults = {
  paused: true,
  healing_mode: "manual",
  dry_run: true,
  allow_automatic: true,
  max_replicas: 5,
  cooldown_seconds: 30,
  max_actions_per_hour: 10,
  retry_limit: 1,
  namespace,
};

function initialState() {
  const timestamp = clock();
  const history = Array.from({ length: 60 }, (_, i) => ({
    ...healthy(i),
    id: id(),
    timestamp: new Date(Date.now() - (59 - i) * 5000).toISOString(),
    source: "demo",
  })).reverse();
  return {
    version: 1,
    scenario: "healthy",
    policy: { ...policyDefaults },
    history,
    alerts: [],
    anomalies: [],
    actions: [],
    audit: [
      {
        id: id(),
        timestamp,
        actor: "showcase-visitor",
        component: "browser-demo",
        action: "showcase_started",
        target: "local-browser",
        result: "simulated",
        rationale:
          "Public interactive demo; all state belongs to this browser session",
        correlation_id: id(),
        severity: "info",
      },
    ],
    faultSamples: 0,
    lastStep: Math.floor(Date.now() / 5000),
  };
}
function healthy(step) {
  return {
    cpu_usage: Number((0.34 + 0.09 * Math.sin(step / 5)).toFixed(3)),
    memory_usage: Number((0.48 + 0.06 * Math.cos(step / 7)).toFixed(3)),
    pod_restarts: 1,
    network_latency: Number((42 + 15 * Math.sin(step / 4)).toFixed(1)),
  };
}
function restore() {
  try {
    const value = JSON.parse(sessionStorage.getItem(KEY));
    if (
      value?.version === 1 &&
      Array.isArray(value.history) &&
      Array.isArray(value.actions) &&
      Array.isArray(value.audit) &&
      Array.isArray(value.alerts) &&
      Array.isArray(value.anomalies)
    ) {
      value.policy = {
        ...policyDefaults,
        healing_mode:
          value.policy?.healing_mode === "recommendation"
            ? "recommendation"
            : "manual",
      };
      value.lastStep = Math.floor(Date.now() / 5000) - 1;
      return value;
    }
  } catch {
    /* Storage can be unavailable; the explicitly simulated session stays usable. */
  }
  return initialState();
}
let state;
function current() {
  if (!state) state = restore();
  return state;
}
function save() {
  const s = current();
  for (const kind of ["history", "alerts", "anomalies", "actions", "audit"])
    s[kind] = s[kind].slice(0, 200);
  try {
    sessionStorage.setItem(KEY, JSON.stringify(s));
  } catch {
    /* Bounded memory fallback; no server persistence claimed. */
  }
}
function audit(action, target, result, rationale, correlation = id()) {
  current().audit.unshift({
    id: id(),
    timestamp: clock(),
    actor: "showcase-visitor",
    component: "browser-demo",
    action,
    target,
    result,
    rationale,
    correlation_id: correlation,
    severity: "info",
  });
}
function workloads() {
  const s = current(),
    rows = [];
  [
    "api-gateway",
    "checkout-service",
    "payment-worker",
    "inventory-api",
    "event-consumer",
    "web-console",
  ].forEach((name, i) => {
    const affected = i === 1 && s.scenario !== "healthy";
    const scaled = s.actions.find(
      (a) =>
        a.target === name &&
        a.action === "scale_deployment" &&
        a.status === "simulated",
    );
    const replicas = scaled?.replicas || (i < 2 ? 3 : 2);
    rows.push({
      id: `deploy-${i}`,
      name,
      namespace,
      kind: "Deployment",
      status: affected ? "Degraded" : "Healthy",
      replicas,
      ready: replicas - (affected ? 1 : 0),
      managed: true,
    });
    for (let p = 0; p < replicas; p++)
      rows.push({
        id: `pod-${i}-${p}`,
        name: `${name}-7d8f-${p}`,
        namespace,
        kind: "Pod",
        status:
          affected && p === 0
            ? s.scenario === "restarts"
              ? "Failed"
              : "Pending"
            : "Running",
        restarts: affected && s.scenario === "restarts" ? 12 : 0,
        node: `demo-worker-${(p % 3) + 1}`,
        managed: true,
      });
  });
  for (let i = 1; i <= 3; i++)
    rows.push({
      id: `node-${i}`,
      name: `demo-worker-${i}`,
      namespace: "cluster",
      kind: "Node",
      status: "Ready",
      managed: false,
    });
  rows.push({
    id: "namespace",
    name: namespace,
    namespace,
    kind: "Namespace",
    status: "Active",
    managed: false,
  });
  return rows;
}
function metrics() {
  return current().history[0];
}
function sample(force = false) {
  const s = current(),
    step = Math.floor(Date.now() / 5000);
  if (!force && step === s.lastStep) return;
  s.lastStep = step;
  const overrides = {
    cpu: { cpu_usage: 0.96 },
    memory: { memory_usage: 0.95 },
    restarts: { pod_restarts: 12 },
    latency: { network_latency: 840 },
  };
  const value = {
    ...healthy(step),
    ...overrides[s.scenario],
    id: id(),
    timestamp: clock(),
    source: "demo",
  };
  s.faultSamples = s.scenario === "healthy" ? 0 : (s.faultSamples || 0) + 1;
  s.history.unshift(value);
  save();
}
function overview() {
  sample();
  automaticStep();
  const s = current(),
    inventory = workloads(),
    pods = inventory.filter((x) => x.kind === "Pod");
  return {
    mode: "demo",
    simulated: true,
    hosting: "browser-showcase",
    cluster: "public-demo",
    connection: {
      kubernetes: "simulated in browser",
      prometheus: "not connected",
      ai: "browser threshold rules; no ML service",
    },
    metrics: metrics(),
    counts: Object.fromEntries(
      ["Node", "Namespace", "Pod", "Deployment"].map((kind) => [
        kind.toLowerCase() + "s",
        inventory.filter((x) => x.kind === kind).length,
      ]),
    ),
    pod_status: Object.fromEntries(
      ["Running", "Pending", "Failed"].map((phase) => [
        phase,
        pods.filter((x) => x.status === phase).length,
      ]),
    ),
    active_alerts: s.alerts.filter((x) => x.status !== "resolved").length,
    anomalies: s.anomalies.length,
    actions: s.actions.slice(0, 5),
    events: s.audit.slice(0, 8),
    worker_updated: metrics().timestamp,
    last_error: null,
    policy: s.policy,
  };
}
function recommend(body, actor = "showcase-visitor", correlation = id()) {
  const s = current();
  if (
    body.namespace !== namespace ||
    !workloads().some(
      (w) => w.kind === "Deployment" && w.managed && w.name === body.target,
    )
  )
    throw new Error("Choose a managed simulated deployment in autohealops.");
  if (!["restart_deployment", "scale_deployment"].includes(body.action))
    throw new Error("Unsupported simulated action.");
  if (
    typeof body.rationale !== "string" ||
    body.rationale.trim().length < 5 ||
    body.rationale.length > 500
  )
    throw new Error("A rationale of 5–500 characters is required.");
  if (
    body.action === "scale_deployment" &&
    (!Number.isInteger(body.replicas) ||
      body.replicas < 1 ||
      body.replicas > s.policy.max_replicas)
  )
    throw new Error("Replicas must be an integer between 1 and 5.");
  const duplicate = s.actions.find(
    (a) =>
      a.action === body.action &&
      a.target === body.target &&
      a.replicas === body.replicas &&
      ["recommended", "approved"].includes(a.status),
  );
  if (duplicate) return duplicate;
  const item = {
    ...body,
    id: id(),
    timestamp: clock(),
    actor,
    correlation_id: correlation,
    status: "recommended",
    before: clone(metrics()),
    after: null,
    result: "Awaiting approval for browser simulation",
    attempts: 0,
    approved_by: null,
    simulated: true,
  };
  s.actions.unshift(item);
  audit("recommend", item.target, "recommended", body.rationale, correlation);
  save();
  return item;
}
function scenario(name) {
  if (!["cpu", "memory", "restarts", "latency", "reset"].includes(name))
    throw new Error("Unknown showcase scenario.");
  const s = current();
  s.faultSamples = 0;
  s.scenario = name === "reset" ? "healthy" : name;
  sample(true);
  if (name === "reset") {
    for (const alert of s.alerts)
      if (alert.status !== "resolved") {
        alert.status = "resolved";
        alert.resolved_at = clock();
      }
  } else if (
    !s.alerts.some((a) => a.scenario === name && a.status !== "resolved")
  ) {
    const feature = {
      cpu: "cpu_usage",
      memory: "memory_usage",
      restarts: "pod_restarts",
      latency: "network_latency",
    }[name];
    const baseline = { cpu: 0.8, memory: 0.85, restarts: 5, latency: 500 }[
      name
    ];
    const correlation = id(),
      explanation = `${feature} ${metrics()[feature]} exceeds threshold ${baseline}. Browser simulation using transparent rules; no ML inference.`;
    const anomaly = {
      id: id(),
      timestamp: clock(),
      is_anomaly: true,
      anomaly_score: null,
      severity: ["cpu", "memory"].includes(name) ? "critical" : "high",
      observations: [
        { feature, value: metrics()[feature], baseline, explanation },
      ],
      explanation,
      model: "browser threshold rules",
      model_version: "browser-rules-v1",
      source: "rule-based",
      measurements: clone(metrics()),
      target: "checkout-service",
      namespace,
      correlation_id: correlation,
      source_mode: "demo",
    };
    s.anomalies.unshift(anomaly);
    s.alerts.unshift({
      id: id(),
      timestamp: clock(),
      severity: anomaly.severity,
      message: explanation,
      status: "open",
      target: anomaly.target,
      correlation_id: correlation,
      anomaly_id: anomaly.id,
      scenario: name,
    });
    audit(
      "anomaly_detected",
      anomaly.target,
      "simulated alert opened",
      explanation,
      correlation,
    );
    recommend(
      {
        action: "restart_deployment",
        namespace,
        target: anomaly.target,
        replicas: null,
        rationale: explanation,
      },
      "browser-detector",
      correlation,
    );
  }
  audit(
    "demo_scenario",
    namespace,
    name,
    "Browser-only scenario; no infrastructure access",
  );
  save();
  return overview();
}
function executeAction(item) {
  const s = current();
  if (item.status === "simulated") return item;
  if (s.policy.paused || s.policy.healing_mode === "recommendation")
    throw new Error(
      "Resume healing in manual approval mode before simulation.",
    );
  const automatic =
    s.policy.healing_mode === "automatic" &&
    item.actor === "browser-detector" &&
    s.faultSamples >= 3;
  if ((!automatic && item.status !== "approved") || item.attempts)
    throw new Error("Explicit approval required; one attempt per action.");
  const recent = s.actions.filter(
    (a) => a.executed_at && Date.now() - Date.parse(a.executed_at) < 3600000,
  );
  if (recent.length >= s.policy.max_actions_per_hour)
    throw new Error("Showcase action budget reached for this hour.");
  if (
    recent.some(
      (a) =>
        a.target === item.target &&
        Date.now() - Date.parse(a.executed_at) <
          s.policy.cooldown_seconds * 1000,
    )
  )
    throw new Error(
      "Target cooldown active. Wait 30 seconds before repeating a simulated recovery.",
    );
  item.before = clone(metrics());
  s.scenario = "healthy";
  sample(true);
  Object.assign(item, {
    status: "simulated",
    attempts: 1,
    executed_at: clock(),
    after: clone(metrics()),
    result: "Simulated recovery only; no Kubernetes operation performed",
  });
  audit(
    "execute_completed",
    item.target,
    "simulated",
    item.result,
    item.correlation_id,
  );
  return item;
}
function automaticStep() {
  const s = current();
  if (
    s.policy.paused ||
    s.policy.healing_mode !== "automatic" ||
    s.faultSamples < 3
  )
    return;
  const item = s.actions.find(
    (a) =>
      a.status === "recommended" &&
      a.actor === "browser-detector" &&
      a.target === "checkout-service",
  );
  if (!item) return;
  try {
    executeAction(item);
    for (const alert of s.alerts) {
      if (alert.correlation_id === item.correlation_id) {
        alert.status = "resolved";
        alert.resolved_at = clock();
      }
    }
  } catch (error) {
    if (s.autoBlocked !== error.message)
      audit(
        "automatic_blocked",
        item.target,
        "blocked",
        error.message,
        item.correlation_id,
      );
    s.autoBlocked = error.message;
  }
}
function list(items, params) {
  let rows = items.filter(
    (x) =>
      (!params.get("q") ||
        JSON.stringify(x)
          .toLowerCase()
          .includes(params.get("q").toLowerCase())) &&
      (!params.get("status") || x.status === params.get("status")),
  );
  const limit = Math.min(200, Math.max(1, Number(params.get("limit")) || 50)),
    offset = Math.max(0, Number(params.get("offset")) || 0);
  return {
    items: rows.slice(offset, offset + limit),
    total: rows.length,
    limit,
    offset,
  };
}
export async function demoRequest(method, path, body = {}) {
  const url = new URL(path, "https://showcase.invalid/"),
    route = url.pathname.replace(/^\//, "");
  const s = current();
  sample();
  let result;
  if (method === "get") {
    if (route === "overview") result = overview();
    else if (route === "clusters")
      result = {
        items: [
          {
            id: "showcase",
            name: "public-demo",
            source: "demo",
            workloads: workloads(),
          },
        ],
        total: 1,
      };
    else if (route === "settings") result = s.policy;
    else if (route === "predictions")
      result = {
        available: false,
        model: "not enabled in public browser demo",
        reason:
          "The hosted showcase uses browser rules. Run the local AI service for trained detection and chronological forecasts.",
      };
    else if (route === "integrations/status")
      result = {
        mode: "demo",
        services: overview().connection,
        storage: "browser session (no server database)",
        notifications: {
          slack: "disabled in public demo",
          email: "disabled in public demo",
        },
        model: "Browser rule-based simulation; no trained ML service",
      };
    else {
      const key = {
        metrics: "history",
        alerts: "alerts",
        incidents: "alerts",
        anomalies: "anomalies",
        "healing/actions": "actions",
        "audit/events": "audit",
      }[route];
      if (!key)
        throw new Error("This endpoint is unavailable in the public demo.");
      result = list(s[key], url.searchParams);
    }
  } else if (method === "put" && route === "settings") {
    if (
      !["manual", "recommendation", "automatic"].includes(body.healing_mode) ||
      typeof body.paused !== "boolean"
    )
      throw new Error("Choose recommendation, manual or automatic simulation.");
    s.policy = {
      ...s.policy,
      paused: body.paused,
      healing_mode: body.healing_mode,
    };
    audit(
      "policy_changed",
      namespace,
      "updated",
      "Browser demo policy updated",
    );
    automaticStep();
    result = s.policy;
  } else if (method === "post" && route === "demo/scenarios")
    result = scenario(body.scenario);
  else if (method === "post" && route === "healing/actions")
    result = recommend(body);
  else if (
    method === "post" &&
    /^healing\/actions\/[^/]+\/(approve|execute)$/.test(route)
  ) {
    const [, , actionId, decision] = route.split("/");
    const item = s.actions.find((a) => a.id === actionId);
    if (!item) throw new Error("Simulated action not found.");
    if (decision === "approve") {
      if (item.status !== "recommended")
        throw new Error("Only recommendations can be approved.");
      if (
        typeof body.rationale !== "string" ||
        body.rationale.trim().length < 5 ||
        body.rationale.length > 500
      )
        throw new Error("A rationale of 5–500 characters is required.");
      Object.assign(item, {
        status: "approved",
        approved_by: "showcase-visitor",
        approval_rationale: body.rationale,
      });
      audit(
        "approve",
        item.target,
        "approved",
        body.rationale,
        item.correlation_id,
      );
    } else if (item.status !== "simulated") {
      executeAction(item);
    }
    result = item;
  } else if (
    method === "post" &&
    /^alerts\/[^/]+\/(acknowledge|resolve)$/.test(route)
  ) {
    const [, alertId, decision] = route.split("/"),
      item = s.alerts.find((a) => a.id === alertId);
    if (!item) throw new Error("Simulated incident not found.");
    item.status = decision === "resolve" ? "resolved" : "acknowledged";
    audit(
      decision,
      item.target,
      item.status,
      "Browser demo incident triage",
      item.correlation_id,
    );
    result = item;
  } else throw new Error("This operation is unavailable in the public demo.");
  save();
  return clone(result);
}
export function subscribeDemo(callback) {
  current();
  callback(overview());
  const timer = setInterval(() => callback(overview()), 5000);
  return () => clearInterval(timer);
}
