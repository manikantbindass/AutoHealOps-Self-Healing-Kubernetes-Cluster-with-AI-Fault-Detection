import React, { useEffect, useState } from "react";
import { Panel } from "../components/UI";
import { usePlatform } from "../hooks/useMetrics";
export default function SettingsPage() {
  const { overview: o, data, mutate, busy } = usePlatform();
  const [mode, setMode] = useState("manual");
  useEffect(() => {
    if (o) setMode(o.policy.healing_mode);
  }, [o]);
  if (!o) return null;
  return (
    <>
      <h1>Settings & integrations</h1>
      <p className="page-description">
        Safe runtime controls and transparent service availability.
      </p>
      <div className="two-col">
        <Panel title="Healing policy" note="ADMINISTRATOR">
          <form
            className="settings-form"
            onSubmit={(e) => {
              e.preventDefault();
              mutate(
                "settings",
                { paused: o.policy.paused, healing_mode: mode },
                "put",
              );
            }}
          >
            <label>
              Operating mode
              <select value={mode} onChange={(e) => setMode(e.target.value)}>
                <option value="recommendation">Recommendation only</option>
                <option value="manual">Manual approval</option>
                {o.policy.allow_automatic && (
                  <option value="automatic">Automatic rollout restart</option>
                )}
              </select>
            </label>
            <p>
              {o.hosting === "browser-showcase"
                ? "Public demo policy is stored in this browser session. All actions are simulated. Automatic execution and infrastructure connections are disabled."
                : "Automatic execution requires ALLOW_AUTOMATIC=true at startup. Scaling always requires approval. Dry-run changes require an environment update and restart."}
            </p>
            <button className="primary" disabled={busy}>
              Save policy
            </button>
          </form>
        </Panel>
        <Panel title="Environment" note={o.mode.toUpperCase()}>
          <div className="info-body">
            <div className="key-value">
              <span>Data provenance</span>
              <strong>
                {o.simulated
                  ? "Simulated telemetry"
                  : "Prometheus / Kubernetes"}
              </strong>
            </div>
            <div className="key-value">
              <span>Storage</span>
              <strong>{data.integrations?.storage}</strong>
            </div>
            <div className="key-value">
              <span>Namespace boundary</span>
              <strong>{o.policy.namespace}</strong>
            </div>
            <p>
              {o.hosting === "browser-showcase"
                ? "This public showcase has no backend database, credentials or cluster connection. Use the repository's local setup for FastAPI, trained ML and persistent storage."
                : "Service URLs, credentials and mode are configured through environment variables. Secret values are never returned to this interface."}
            </p>
          </div>
        </Panel>
      </div>
      <Panel title="Service connections" note="ACTUAL STATUS">
        <div className="integration-grid">
          {Object.entries(data.integrations?.services || {}).map(
            ([name, status]) => (
              <div key={name}>
                <span className="eyebrow">{name}</span>
                <h3>{status}</h3>
              </div>
            ),
          )}
        </div>
        <div className="info-body">
          <p>
            Slack: {data.integrations?.notifications?.slack}. Email:{" "}
            {data.integrations?.notifications?.email}. Configure optional
            destinations through environment variables. Multi-cluster
            connections and destination editing are planned.
          </p>
        </div>
      </Panel>
    </>
  );
}
