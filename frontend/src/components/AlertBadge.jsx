import React from "react";
export default function AlertBadge({ severity }) {
  return (
    <span className={`badge ${String(severity).toLowerCase()}`}>
      <i />
      {severity}
    </span>
  );
}
