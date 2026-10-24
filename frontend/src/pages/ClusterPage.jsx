import React, { useState, useRef } from "react";
import { Panel, Filters, Empty } from "../components/UI";
import AlertBadge from "../components/AlertBadge";
import { usePlatform } from "../hooks/useMetrics";
export default function ClusterPage() {
  const opener = useRef(null);
  const close = () => {
    setDetail(null);
    opener.current?.focus();
  };
  const { data, refresh } = usePlatform();
  const [search, setSearch] = useState(""),
    [filter, setFilter] = useState(""),
    [detail, setDetail] = useState(null);
  const rows = (data.clusters?.items?.[0]?.workloads || []).filter(
    (x) =>
      (!filter || x.kind === filter) &&
      `${x.name} ${x.namespace} ${x.status}`
        .toLowerCase()
        .includes(search.toLowerCase()),
  );
  return (
    <>
      <div className="title-row">
        <div>
          <h1>Cluster explorer</h1>
          <p className="page-description">
            Inspect the resources available within your authorization boundary.
          </p>
        </div>
        <button onClick={refresh}>Refresh resources</button>
      </div>
      <Filters
        {...{ search, setSearch, filter, setFilter }}
        options={["Deployment", "Pod", "Node", "Namespace"]}
      />
      <Panel title="Resource inventory" note={`${rows.length} resources`}>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Resource</th>
                <th>Kind</th>
                <th>Namespace</th>
                <th>Status</th>
                <th>Details</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((x) => (
                <tr key={x.id}>
                  <td className="mono">{x.name}</td>
                  <td>{x.kind}</td>
                  <td className="muted">{x.namespace}</td>
                  <td>
                    <AlertBadge severity={x.status} />
                  </td>
                  <td>
                    <button
                      onClick={(e) => {
                        opener.current = e.currentTarget;
                        setDetail(x);
                      }}
                    >
                      Inspect
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {!rows.length && <Empty />}
        </div>
      </Panel>
      {detail && (
        <div className="modal-backdrop" onClick={close}>
          <section
            className="detail-panel"
            role="dialog"
            aria-modal="true"
            aria-label="Resource details"
            onKeyDown={(e) => {
              if (e.key === "Escape") {
                e.preventDefault();
                close();
              }
              if (e.key === "Tab") {
                e.preventDefault();
                e.currentTarget.querySelector("button").focus();
              }
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <button autoFocus onClick={close}>
              Close details
            </button>
            <h2>{detail.name}</h2>
            <dl>
              {Object.entries(detail).map(([k, v]) => (
                <div className="key-value" key={k}>
                  <dt>{k}</dt>
                  <dd>{String(v)}</dd>
                </div>
              ))}
            </dl>
          </section>
        </div>
      )}
    </>
  );
}
