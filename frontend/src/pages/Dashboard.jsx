import React, { useState } from "react";
import { Link } from "react-router-dom";
import {
  Cpu,
  MemoryStick,
  Boxes,
  ShieldCheck,
  ArrowRight,
  Activity,
  CircleDot,
} from "lucide-react";
import MetricCard from "../components/MetricCard";
import AlertBadge from "../components/AlertBadge";
import { Panel, Trend, Empty, date } from "../components/UI";
import { usePlatform } from "../hooks/useMetrics";
export default function Dashboard() {
  const { overview: o, data, mutate, busy } = usePlatform();
  const [range, setRange] = useState("15");
  if (!o) return null;
  const m = o.metrics;
  const history = (data.history?.items || []).filter(
    (x) => Date.now() - Date.parse(x.timestamp) <= Number(range) * 60000,
  );
  const deployments =
    data.clusters?.items?.[0]?.workloads.filter(
      (x) => x.kind === "Deployment",
    ) || [];
  return (
    <>
      <div className="page-title">
        <div className="eyebrow">WORKSPACE / {o.cluster.toUpperCase()}</div>
        <div className="title-row">
          <div>
            <h1>Operations overview</h1>
            <p>
              A clear view of your infrastructure. A safer path to recovery.
            </p>
          </div>
          <div className="title-actions">
            <span className="badge info">
              <CircleDot size={12} />
              {o.counts.namespaces} namespace
            </span>
            <select
              aria-label="Dashboard time range"
              value={range}
              onChange={(e) => setRange(e.target.value)}
            >
              <option value="5">Last 5 minutes</option>
              <option value="15">Last 15 minutes</option>
              <option value="60">Last hour</option>
            </select>
          </div>
        </div>
      </div>
      <div className="health-strip">
        <div className={`health-icon ${o.active_alerts ? "amber" : "green"}`}>
          <ShieldCheck size={23} />
        </div>
        <div>
          <strong>
            {o.active_alerts
              ? "Your cluster needs attention"
              : m
                ? "Your cluster is operating normally"
                : "Waiting for cluster telemetry"}
          </strong>
          <p>
            {o.active_alerts} active alerts · {o.counts.deployments} deployments
            monitored ·{" "}
            {o.simulated
              ? "Demonstration environment"
              : "Namespace-scoped monitoring"}
          </p>
        </div>
        <Link to="/healing">
          Review healing policy <ArrowRight size={14} />
        </Link>
      </div>
      <div className="metric-grid">
        <MetricCard
          title="CPU utilization"
          value={m?.cpu_usage != null ? (m.cpu_usage * 100).toFixed(1) : null}
          unit="%"
          icon={Cpu}
          subtext="Normalized utilization"
          color="blue"
        />
        <MetricCard
          title="Memory utilization"
          value={
            m?.memory_usage != null ? (m.memory_usage * 100).toFixed(1) : null
          }
          unit="%"
          icon={MemoryStick}
          subtext="Fraction of configured limits"
          color="purple"
        />
        <MetricCard
          title="Running pods"
          value={o.pod_status.Running}
          unit={`/ ${o.counts.pods}`}
          icon={Boxes}
          subtext={`${o.pod_status.Pending} pending · ${o.pod_status.Failed} failed`}
        />
        <MetricCard
          title="Fault detections"
          value={o.anomalies}
          icon={Activity}
          subtext={`${o.active_alerts} alerts need review`}
          color={o.active_alerts ? "amber" : "green"}
        />
      </div>
      <div className="dashboard-grid">
        <Panel
          title="Resource utilization"
          note={
            <>
              <span className="legend blue">CPU</span>
              <span className="legend purple">Memory</span>
            </>
          }
        >
          <Trend history={history} />
          <div className="chart-footer">
            <span>Utilization · percent of capacity</span>
            <span>Collected every 5s in default configuration</span>
          </div>
        </Panel>
        <Panel title="Control plane" note="POLICY">
          <div className="policy-visual">
            <ShieldCheck size={34} />
            <strong>
              {o.policy.paused ? "Healing is paused" : "Healing is enabled"}
            </strong>
            <p>
              {o.policy.dry_run
                ? "Dry-run safeguards active"
                : "Live mutations explicitly enabled"}
            </p>
          </div>
          <div className="key-value">
            <span>Execution mode</span>
            <strong>{o.policy.healing_mode}</strong>
          </div>
          <div className="key-value">
            <span>Concurrent actions</span>
            <strong>1 maximum</strong>
          </div>
          <div className="key-value">
            <span>Target cooldown</span>
            <strong>{o.policy.cooldown_seconds}s</strong>
          </div>
          <Link className="panel-link" to="/healing">
            Manage healing operations <ArrowRight size={14} />
          </Link>
        </Panel>
      </div>
      <div className="dashboard-grid">
        <Panel
          title="Workload health"
          note={
            <Link to="/cluster">
              Explore cluster <ArrowRight size={12} />
            </Link>
          }
        >
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Deployment</th>
                  <th>Namespace</th>
                  <th>Replicas</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {deployments.slice(0, 5).map((w) => (
                  <tr key={w.id}>
                    <td>
                      <span className="resource-icon">
                        <Boxes size={14} />
                      </span>
                      {w.name}
                    </td>
                    <td className="muted">{w.namespace}</td>
                    <td className="mono">
                      {w.ready}/{w.replicas}
                    </td>
                    <td>
                      <AlertBadge severity={w.status} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {!deployments.length && <Empty />}
          </div>
        </Panel>
        <Panel
          title="Activity feed"
          note={
            <Link to="/logs">
              View audit <ArrowRight size={12} />
            </Link>
          }
        >
          <div className="timeline">
            {o.events.slice(0, 4).map((e) => (
              <div className="timeline-item" key={e.id}>
                <span className="timeline-dot" />
                <div>
                  <strong>{e.action.replaceAll("_", " ")}</strong>
                  <p>
                    {e.target} · {e.result}
                  </p>
                  <time>{date(e.timestamp)}</time>
                </div>
              </div>
            ))}
          </div>
        </Panel>
      </div>
      {o.simulated && (
        <Panel title="Scenario lab" note="SIMULATED DATA ONLY">
          <div className="scenario-row">
            <p>
              Inject a reproducible fault and follow detection → approval →
              simulated recovery.
            </p>
            <div>
              {["cpu", "memory", "restarts", "latency", "reset"].map((s) => (
                <button
                  key={s}
                  disabled={busy}
                  onClick={() => mutate("demo/scenarios", { scenario: s })}
                >
                  {s === "reset"
                    ? "Reset scenario"
                    : `${s.toUpperCase()} spike`}
                </button>
              ))}
            </div>
          </div>
        </Panel>
      )}
    </>
  );
}
