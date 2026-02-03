import React from "react";
import ProbabilityRow, { type ProbabilityRowProps } from "./ProbabilityRow";

export type ConfidenceLevel = "high" | "medium" | "low";

export interface MarketCardProps {
  title: string;
  rows: ProbabilityRowProps[];
  /** Optional badge label (e.g. "High"); hidden if null/empty */
  confidenceLabel?: string | null;
  /** Optional level for styling (high/medium/low) */
  confidenceLevel?: ConfidenceLevel | null;
}

export default function MarketCard({ title, rows, confidenceLabel, confidenceLevel }: MarketCardProps) {
  const showConfidence = confidenceLabel != null && confidenceLabel !== "" && confidenceLevel != null;
  return (
    <article className="ai-marketCard">
      <header className="ai-marketCard__header">
        <h3 className="ai-marketCard__title">{title}</h3>
        {showConfidence && (
          <span className={`ai-marketCard__confidence ai-marketCard__confidence--${confidenceLevel}`} title={confidenceLabel} aria-hidden>
            {confidenceLabel}
          </span>
        )}
      </header>
      <div className="ai-marketCard__body">
        {rows.length === 0 ? (
          <p className="ai-marketCard__empty">—</p>
        ) : (
          rows.map((row, idx) => (
            <ProbabilityRow
              key={`${row.label}-${idx}`}
              label={row.label}
              percent={row.percent}
              recommended={row.recommended}
            />
          ))
        )}
      </div>
    </article>
  );
}

