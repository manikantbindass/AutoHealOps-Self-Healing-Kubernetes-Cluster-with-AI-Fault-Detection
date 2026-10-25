import React, { useState } from "react";
import { Panel, Empty, date } from "../components/UI";
import AlertBadge from "../components/AlertBadge";
import { usePlatform } from "../hooks/useMetrics";
export default function HealingPage() {
  const { overview: o, data, mutate, busy } = usePlatform();
  const [rationale, setRationale] = useState(
    "Reviewed evidence and approved controlled recovery",
  );
  const [target, setTarget] = useState(""),
    [action, setAction] = useState("restart_deployment"),
    [replicas, setReplicas] = useState(2);
  if (!o) return null;
  const policy = o.policy;
  const targets = (data.clusters?.items?.[0]?.workloads || []).filter(
    (x) => x.kind === "Deployment" && x.managed,
  );
  return (
    <>
      <h1>Healing operations</h1>
      <p className="page-description">
        Review evidence, follow autonomous recovery or approve a bounded action.
      </p>
      <div className="policy-bar">
        <div>
          <AlertBadge severity={policy.paused ? "paused" : "enabled"} />
          <span>
            {policy.healing_mode} ·{" "}
            {policy.dry_run ? "dry-run" : "live execution"} · max{" "}
            {policy.max_replicas} replicas · cooldown {policy.cooldown_seconds}s
          </span>
        </div>
        <button
          className={policy.paused ? "primary" : "danger"}
          disabled={busy}
          onClick={() =>
            mutate(
              "settings",
              { paused: !policy.paused, healing_mode: policy.healing_mode },
              "put",
            )
          }
        >
          {policy.paused ? "Resume healing" : "Emergency pause"}
        </button>
      </div>
      <Panel title="Create a recommendation" note="EXPLICIT TARGET">
        <form
          className="action-form"
          onSubmit={(e) => {
            e.preventDefault();
            mutate("healing/actions", {
              target,
              namespace: policy.namespace,
              action,
              replicas: action === "scale_deployment" ? Number(replicas) : null,
              rationale,
            });
          }}
        >
          <label>
            Managed deployment
            <select
              required
              value={target}
              onChange={(e) => setTarget(e.target.value)}
            >
              <option value="">Select deployment</option>
              {targets.map((x) => (
                <option key={x.id} value={x.name}>
                  {x.name}
                </option>
              ))}
            </select>
          </label>
          <label>
            Action
            <select value={action} onChange={(e) => setAction(e.target.value)}>
              <option value="restart_deployment">Rollout restart</option>
              <option value="scale_deployment">Scale deployment</option>
            </select>
          </label>
          {action === "scale_deployment" && (
            <label>
              Replicas
              <input
                type="number"
                required
                min="1"
                max={policy.max_replicas}
                value={replicas}
                onChange={(e) => setReplicas(e.target.value)}
              />
            </label>
          )}
          <label className="grow">
            Decision rationale
            <input
              required
              minLength="5"
              maxLength="500"
              value={rationale}
              onChange={(e) => setRationale(e.target.value)}
            />
          </label>
          <button disabled={busy} type="submit">
            Recommend action
          </button>
        </form>
      </Panel>
      <Panel title="Recommendations & execution history" note="LATEST 200">
        {(data.actions?.items || []).map((x) => (
          <article className="record" key={x.id}>
            <div className="record-top">
              <AlertBadge severity={x.status} />
              <span>{x.action.replaceAll("_", " ")}</span>
              <time>{date(x.timestamp)}</time>
            </div>
            <h3>
              {x.target} <span className="muted">/ {x.namespace}</span>
            </h3>
            <p>{x.rationale}</p>
            <p className="result">
              {typeof x.result === "string"
                ? x.result
                : JSON.stringify(x.result)}
            </p>
            <small>
              {x.approved_by
                ? `Approved by ${x.approved_by}`
                : x.attempts > 0
                  ? "Authorized by automatic policy"
                  : "Awaiting authorization"}{" "}
              · attempts {x.attempts}/1 · correlation {x.correlation_id}
            </small>
            {x.before && (
              <div className="evidence">
                <div>
                  <span>CPU before / after</span>
                  <strong>
                    {(x.before.cpu_usage * 100).toFixed(1)}% /{" "}
                    {x.after ? `${(x.after.cpu_usage * 100).toFixed(1)}%` : "—"}
                  </strong>
                </div>
                <div>
                  <span>Memory before / after</span>
                  <strong>
                    {(x.before.memory_usage * 100).toFixed(1)}% /{" "}
                    {x.after
                      ? `${(x.after.memory_usage * 100).toFixed(1)}%`
                      : "—"}
                  </strong>
                </div>
              </div>
            )}
            <div className="record-actions">
              {x.status === "recommended" && (
                <button
                  disabled={busy || rationale.length < 5}
                  onClick={() =>
                    mutate(`healing/actions/${x.id}/approve`, { rationale })
                  }
                >
                  Approve action
                </button>
              )}
              {x.status === "approved" && (
                <button
                  className="primary"
                  disabled={
                    busy ||
                    policy.paused ||
                    policy.healing_mode === "recommendation"
                  }
                  onClick={() => mutate(`healing/actions/${x.id}/execute`)}
                >
                  {o.simulated
                    ? "Simulate recovery"
                    : policy.dry_run
                      ? "Execute dry-run"
                      : "Execute approved action"}
                </button>
              )}
            </div>
          </article>
        ))}
        {!data.actions?.items?.length && (
          <Empty>
            No recovery actions yet. Inject a simulated fault or recommend an
            action for an opted-in deployment.
          </Empty>
        )}
      </Panel>
    </>
  );
}
