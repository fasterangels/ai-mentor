import React from "react";

export interface FinalPredictionCardProps {
  matchLabel: string;
  metaLine?: string;
  modeLabel: string;
  summary?: string;
  statusLabel?: string;
  reasoning?: string;
}

export default function FinalPredictionCard({
  matchLabel,
  metaLine,
  modeLabel,
  summary,
  statusLabel,
  reasoning,
}: FinalPredictionCardProps) {
  return (
    <section className="ai-finalPrediction" aria-label={matchLabel}>
      <header className="ai-finalPrediction__header">
        <div>
          <h2 className="ai-finalPrediction__match">{matchLabel}</h2>
          {metaLine && <p className="ai-finalPrediction__meta">{metaLine}</p>}
        </div>
        <div className="ai-finalPrediction__pills">
          <span className="ai-finalPrediction__mode">{modeLabel}</span>
          {statusLabel && <span className="ai-finalPrediction__status">{statusLabel}</span>}
        </div>
      </header>
      {summary && <p className="ai-finalPrediction__summary">{summary}</p>}
      {reasoning && <p className="ai-finalPrediction__reasoning">{reasoning}</p>}
    </section>
  );
}

