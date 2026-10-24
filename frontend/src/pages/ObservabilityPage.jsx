import React, { useState } from "react";
import { Panel, Trend } from "../components/UI";
import { usePlatform } from "../hooks/useMetrics";
export default function ObservabilityPage() {
  const { data } = usePlatform();
  const [range, setRange] = useState("15");
  const history = (data.history?.items || []).filter(
    (x) => Date.now() - Date.parse(x.timestamp) <= Number(range) * 60000,
  );
  return (
    <>
      <div className="title-row">
        <div>
          <h1>Observability</h1>
          <p className="page-description">
            Persisted telemetry with explicit units and collection timestamps.
          </p>
        </div>
        <select
          aria-label="Metric time range"
          value={range}
          onChange={(e) => setRange(e.target.value)}
        >
          <option value="5">Last 5 minutes</option>
          <option value="15">Last 15 minutes</option>
          <option value="60">Last hour</option>
        </select>
      </div>
      <Panel title="CPU & memory utilization" note="PERCENT">
        <Trend history={history} />
      </Panel>
      <div className="two-col">
        <Panel title="Network latency" note="MILLISECONDS">
          <Trend history={history} latency />
        </Panel>
        <Panel title="Pod restarts" note="COUNT">
          <Trend history={history} restarts />
        </Panel>
      </div>
      <p className="muted">
        Showing up to 200 retained samples. Live latency requires instrumented
        workload histograms; CPU and memory require resource limits and
        Kubernetes exporters.
      </p>
    </>
  );
}
