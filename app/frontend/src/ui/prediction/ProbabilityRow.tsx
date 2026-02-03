import React from "react";

export interface ProbabilityRowProps {
  label: string;
  percent?: number | null;
  recommended?: boolean;
}

export default function ProbabilityRow({ label, percent, recommended }: ProbabilityRowProps) {
  const pct = typeof percent === "number" && !Number.isNaN(percent) ? Math.max(0, Math.min(100, percent)) : null;
  return (
    <div className="ai-probRow">
      <div className="ai-probRow__label">
        <span>{label || "—"}</span>
        {recommended && <span className="ai-probRow__tag">REC</span>}
      </div>
      <div className="ai-probRow__meta">
        <span className="ai-probRow__value">{pct != null ? `${pct}%` : "—"}</span>
        <div className="ai-progress" aria-hidden>
          <div className="ai-progress__bar" style={{ width: pct != null ? `${pct}%` : "0%" }} />
        </div>
      </div>
    </div>
  );
}

