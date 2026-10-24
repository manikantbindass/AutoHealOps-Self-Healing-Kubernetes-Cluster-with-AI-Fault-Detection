import React from "react";
import {
  AreaChart,
  Area,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
export const date = (value) =>
  value
    ? new Date(value).toLocaleString(undefined, {
        month: "short",
        day: "2-digit",
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
      })
    : "—";
export function Empty({ children = "No records match this view." }) {
  return <div className="empty">{children}</div>;
}
export function Panel({ title, note, children, className = "" }) {
  return (
    <section className={`panel ${className}`}>
      <div className="panel-heading">
        <h2>{title}</h2>
        <span>{note}</span>
      </div>
      {children}
    </section>
  );
}
export function Trend({ history = [], latency = false, restarts = false }) {
  const data = [...history].reverse().map((x) => ({
    ...x,
    time: new Date(x.timestamp).toLocaleTimeString([], {
      hour: "2-digit",
      minute: "2-digit",
    }),
    cpu: x.cpu_usage == null ? null : Math.round(x.cpu_usage * 1000) / 10,
    memory:
      x.memory_usage == null ? null : Math.round(x.memory_usage * 1000) / 10,
  }));
  if (!data.length)
    return <Empty>No telemetry available. Check collector integrations.</Empty>;
  const Chart = latency || restarts ? LineChart : AreaChart;
  return (
    <div
      className="chart"
      role="img"
      aria-label={
        latency
          ? "Network latency trend in milliseconds"
          : restarts
            ? "Pod restart count trend"
            : "CPU and memory utilization over time in percent"
      }
    >
      <ResponsiveContainer width="100%" height="100%">
        <Chart
          data={data}
          margin={{ top: 15, right: 15, bottom: 0, left: -20 }}
        >
          <defs>
            <linearGradient id="cpu-fill" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#6a9aff" stopOpacity={0.22} />
              <stop offset="100%" stopColor="#6a9aff" stopOpacity={0} />
            </linearGradient>
            <linearGradient id="mem-fill" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#a897ed" stopOpacity={0.12} />
              <stop offset="100%" stopColor="#a897ed" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid
            vertical={false}
            stroke="#253040"
            strokeDasharray="3 4"
          />
          <XAxis
            dataKey="time"
            minTickGap={70}
            tick={{ fill: "#8793a6", fontSize: 10 }}
            axisLine={false}
            tickLine={false}
          />
          <YAxis
            domain={latency || restarts ? ["auto", "auto"] : [0, 100]}
            tick={{ fill: "#8793a6", fontSize: 10 }}
            axisLine={false}
            tickLine={false}
            unit={latency ? "ms" : restarts ? "" : "%"}
          />
          <Tooltip
            contentStyle={{
              background: "#172131",
              border: "1px solid #334155",
              borderRadius: 8,
              color: "#e2e8f0",
            }}
          />
          {latency || restarts ? (
            <Line
              isAnimationActive={false}
              dataKey={latency ? "network_latency" : "pod_restarts"}
              name={latency ? "Latency (ms)" : "Restarts (count)"}
              stroke="#67d7bb"
              strokeWidth={2}
              dot={false}
            />
          ) : (
            <>
              <Area
                isAnimationActive={false}
                type="monotone"
                dataKey="cpu"
                name="CPU %"
                stroke="#6a9aff"
                fill="url(#cpu-fill)"
                strokeWidth={2}
              />
              <Area
                isAnimationActive={false}
                type="monotone"
                dataKey="memory"
                name="Memory %"
                stroke="#a897ed"
                fill="url(#mem-fill)"
                strokeWidth={2}
              />
            </>
          )}
        </Chart>
      </ResponsiveContainer>
    </div>
  );
}
export function Filters({
  search,
  setSearch,
  filter,
  setFilter,
  options,
  placeholder = "Search resources, events…",
}) {
  return (
    <div className="filters">
      <input
        aria-label="Search records"
        placeholder={placeholder}
        value={search}
        onChange={(e) => setSearch(e.target.value)}
      />
      <select
        aria-label="Filter records"
        value={filter}
        onChange={(e) => setFilter(e.target.value)}
      >
        <option value="">All statuses</option>
        {options.map((o) => (
          <option key={o}>{o}</option>
        ))}
      </select>
    </div>
  );
}
