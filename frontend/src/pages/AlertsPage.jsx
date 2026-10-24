import React, { useState } from "react";
import { Panel, Filters, Empty, date } from "../components/UI";
import AlertBadge from "../components/AlertBadge";
import { usePlatform } from "../hooks/useMetrics";
export default function AlertsPage() {
  const { data, mutate, busy } = usePlatform();
  const [search, setSearch] = useState(""),
    [filter, setFilter] = useState("");
  const rows = (data.alerts?.items || []).filter(
    (x) =>
      (!filter || x.severity === filter) &&
      `${x.message} ${x.target} ${x.status}`
        .toLowerCase()
        .includes(search.toLowerCase()),
  );
  return (
    <>
      <h1>Alerts & incidents</h1>
      <p className="page-description">
        Triage detections, acknowledge ownership, and track resolution.
      </p>
      <Filters
        {...{ search, setSearch, filter, setFilter }}
        options={["critical", "high", "medium", "low"]}
      />
      <Panel
        title="Incident history"
        note={`${rows.length} matching records · latest 200`}
      >
        {rows.map((x) => (
          <article className="record" key={x.id}>
            <div className="record-top">
              <AlertBadge severity={x.severity} />
              <span className="mono muted">{date(x.timestamp)}</span>
              <AlertBadge severity={x.status} />
            </div>
            <h3>{x.target}</h3>
            <p>{x.message}</p>
            <small>Correlation: {x.correlation_id}</small>
            <div className="record-actions">
              <button
                disabled={busy || x.status !== "open"}
                onClick={() => mutate(`alerts/${x.id}/acknowledge`)}
              >
                Acknowledge
              </button>
              <button
                disabled={busy || x.status === "resolved"}
                onClick={() => mutate(`alerts/${x.id}/resolve`)}
              >
                Resolve incident
              </button>
            </div>
          </article>
        ))}
        {!rows.length && (
          <Empty>
            No incidents match. Inject a fault in the scenario lab to test the
            workflow.
          </Empty>
        )}
      </Panel>
    </>
  );
}
