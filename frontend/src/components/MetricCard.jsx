import React from "react";
import { Activity, ArrowUpRight } from "lucide-react";
export default function MetricCard({
  title,
  value,
  unit,
  icon: Icon = Activity,
  subtext,
  color = "green",
}) {
  return (
    <div className="metric-card">
      <div className="metric-label">
        {title}
        <Icon size={17} />
      </div>
      <div className="metric-value">
        {value ?? "—"}
        <span>{unit}</span>
      </div>
      <div className={`metric-note ${color}`}>
        <ArrowUpRight size={13} />
        {subtext}
      </div>
    </div>
  );
}
