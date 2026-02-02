import type { EvaluationKPI } from "./types";

export interface EvaluationPanelProps {
  /** Read-only KPIs; panel renders only when length > 0. */
  items: EvaluationKPI[] | undefined;
}

/**
 * BLOCK 1 — Evaluation visibility. Read-only KPIs from evaluation_v2 / analyzer.analysis_run.
 * Renders only if evaluation data exists. Minimal styling, consistent with existing cards.
 */
export default function EvaluationPanel({ items }: EvaluationPanelProps) {
  if (items == null || items.length === 0) return null;

  return (
    <div className="ai-section">
      <div className="ai-card" style={{ flex: "1 1 100%", minWidth: 0 }}>
        <div className="ai-cardHeader">
          <div className="ai-cardTitle">{require("../../i18n").t("section.evaluation")}</div>
        </div>
      <ul style={{ margin: "4px 0 0 0", paddingLeft: 20, listStyle: "disc", fontSize: 14 }}>
        {items.map((kpi, i) => (
          <li key={i} style={{ marginBottom: 4 }}>
            <span className="ai-status-label">{kpi.label}:</span>{" "}
            {typeof kpi.value === "number" ? kpi.value : kpi.value}
            {kpi.unit != null && kpi.unit !== "" && (
              <span className="ai-muted" style={{ marginLeft: 4 }}>{kpi.unit}</span>
            )}
          </li>
        ))}
      </ul>
      </div>
    </div>
  );
}
