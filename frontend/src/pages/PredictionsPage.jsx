import React, { useState } from "react";
import { Panel, Filters, Empty, date } from "../components/UI";
import AlertBadge from "../components/AlertBadge";
import { usePlatform } from "../hooks/useMetrics";
export default function PredictionsPage() {
  const { data } = usePlatform();
  const [search, setSearch] = useState(""),
    [filter, setFilter] = useState("");
  const p = data.predictions;
  const rows = (data.anomalies?.items || []).filter(
    (x) =>
      (!filter || x.severity === filter) &&
      `${x.target} ${x.explanation}`
        .toLowerCase()
        .includes(search.toLowerCase()),
  );
  return (
    <>
      <h1>AI fault intelligence</h1>
      <p className="page-description">
        Explainable anomaly detection, with honest model and forecast
        limitations.
      </p>
      <div className="two-col">
        <Panel title="Anomaly detection" note="MODEL IDENTITY">
          <div className="info-body">
            <h3>
              {data.integrations?.services?.ai || "Checking availability"}
            </h3>
            <p>
              Isolation Forest when a compatible artifact is loaded; transparent
              threshold rules otherwise. Scores describe deviation, never
              probability of failure.
            </p>
          </div>
        </Panel>
        <Panel title="Metric forecast" note={p?.model || "UNAVAILABLE"}>
          <div className="info-body">
            {p?.available ? (
              <>
                <div className="forecast-values">
                  <span>
                    <strong>{(p.forecast.cpu_usage * 100).toFixed(1)}%</strong>
                    CPU forecast
                  </span>
                  <span>
                    <strong>
                      {(p.forecast.memory_usage * 100).toFixed(1)}%
                    </strong>
                    Memory forecast
                  </span>
                </div>
                <p>
                  Horizon {p.horizon_seconds.toFixed(0)} seconds · refreshed{" "}
                  {date(p.data_freshness)}
                </p>
                <p>
                  Chronological holdout MAE: trend{" "}
                  {p.evaluation.linear_mae_fraction.toFixed(4)} / persistence{" "}
                  {p.evaluation.persistence_mae_fraction.toFixed(4)}.
                </p>
              </>
            ) : (
              <p>{p?.reason || "Loading forecast…"}</p>
            )}
            <small>
              No calibrated failure probability, time-to-failure, or confidence
              is available.
            </small>
          </div>
        </Panel>
      </div>
      <Filters
        {...{ search, setSearch, filter, setFilter }}
        options={["critical", "high", "low"]}
      />
      <Panel title="Detection evidence" note="LATEST 200">
        {rows.map((x) => (
          <article className="record" key={x.id}>
            <div className="record-top">
              <AlertBadge severity={x.severity} />
              <span>
                {x.source} · {x.model_version}
              </span>
              <time>{date(x.timestamp)}</time>
            </div>
            <h3>{x.target}</h3>
            <p>{x.explanation}</p>
            <div className="evidence">
              {x.observations.map((o) => (
                <div key={o.feature}>
                  <span>{o.feature}</span>
                  <strong>{o.value}</strong>
                  <small>Threshold {o.baseline}</small>
                </div>
              ))}
            </div>
            <small>
              Decision score:{" "}
              {x.anomaly_score == null
                ? "not applicable (rules)"
                : x.anomaly_score.toFixed(4)}{" "}
              · Correlation {x.correlation_id}
            </small>
          </article>
        ))}
        {!rows.length && (
          <Empty>
            No anomalies recorded. Use the scenario lab to generate a
            transparent detection.
          </Empty>
        )}
      </Panel>
    </>
  );
}
