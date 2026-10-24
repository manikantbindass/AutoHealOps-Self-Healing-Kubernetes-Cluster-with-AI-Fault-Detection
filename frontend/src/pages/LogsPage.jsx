import React, { useState } from "react";
import { Panel, Filters, Empty, date } from "../components/UI";
import { usePlatform } from "../hooks/useMetrics";
export default function LogsPage() {
  const { data } = usePlatform();
  const [search, setSearch] = useState(""),
    [filter, setFilter] = useState(""),
    [since, setSince] = useState(""),
    [component, setComponent] = useState(""),
    [action, setAction] = useState("");
  const all = data.audit?.items || [];
  const rows = all.filter(
    (x) =>
      (!filter || x.severity === filter) &&
      (!component || x.component === component) &&
      (!action || x.action === action) &&
      (!since || Date.parse(x.timestamp) >= Date.parse(since)) &&
      JSON.stringify(x).toLowerCase().includes(search.toLowerCase()),
  );
  return (
    <>
      <h1>Events & audit logs</h1>
      <p className="page-description">
        Actor, decision, result, and correlation across the operational
        lifecycle.
      </p>
      <Filters
        {...{ search, setSearch, filter, setFilter }}
        options={["info", "high", "critical", "error"]}
      />
      <div className="filters">
        <label>
          Since{" "}
          <input
            aria-label="Events since"
            type="datetime-local"
            value={since}
            onChange={(e) => setSince(e.target.value)}
          />
        </label>
        <select
          aria-label="Component"
          value={component}
          onChange={(e) => setComponent(e.target.value)}
        >
          <option value="">All components</option>
          {[...new Set(all.map((x) => x.component))].map((x) => (
            <option key={x}>{x}</option>
          ))}
        </select>
        <select
          aria-label="Action"
          value={action}
          onChange={(e) => setAction(e.target.value)}
        >
          <option value="">All actions</option>
          {[...new Set(all.map((x) => x.action))].map((x) => (
            <option key={x}>{x}</option>
          ))}
        </select>
      </div>
      <Panel title="Audit trail" note={`${rows.length} matching · latest 200`}>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                {[
                  "Timestamp",
                  "Actor / component",
                  "Action / resource",
                  "Result",
                  "Rationale / correlation",
                ].map((x) => (
                  <th key={x}>{x}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((x) => (
                <tr key={x.id}>
                  <td className="mono">{date(x.timestamp)}</td>
                  <td>
                    {x.actor}
                    <small>{x.component}</small>
                  </td>
                  <td>
                    {x.action}
                    <small>{x.target}</small>
                  </td>
                  <td>{x.result}</td>
                  <td className="log-rationale">
                    {x.rationale}
                    <small className="mono">{x.correlation_id}</small>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {!rows.length && <Empty />}
        </div>
      </Panel>
    </>
  );
}
