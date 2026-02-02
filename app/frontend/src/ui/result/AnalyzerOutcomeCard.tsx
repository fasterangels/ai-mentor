import { t, labelAnalyzerOutcome } from "../../i18n";
import type { AnalyzerVM } from "./types";

export interface AnalyzerOutcomeCardProps {
  analyzer: AnalyzerVM;
}

export default function AnalyzerOutcomeCard({ analyzer }: AnalyzerOutcomeCardProps) {
  const outcome = analyzer.outcome || "UNKNOWN";
  const isPrediction = /^PREDICTION_AVAILABLE|^OK$/i.test(outcome);
  const isNoPrediction = /^NO_PREDICTION|NO_BET|NO_DECISION$/i.test(outcome);

  const outcomeClass = isPrediction ? "ai-chip--success" : isNoPrediction ? "ai-chip--warn" : "";

  return (
    <div className="ai-card" style={{ flex: "1 1 280px", minWidth: 0 }}>
      <div className="ai-cardHeader">
        <div className="ai-cardTitle">{t("section.analyzer")}</div>
      </div>
      <p style={{ margin: "4px 0", fontSize: 14 }}>
        <span className="ai-status-label">{t("label.outcome")}:</span>{" "}
        <span className={outcomeClass ? `ai-chip ${outcomeClass}` : ""}>
          {labelAnalyzerOutcome(outcome)}
        </span>
      </p>
      {analyzer.statusLabel && (
        <p className="ai-muted" style={{ margin: "4px 0", fontSize: 13 }}>
          <span className="ai-status-label">{t("label.status")}:</span> {analyzer.statusLabel}
          {analyzer.logicVersion != null && analyzer.logicVersion !== "" && (
            <> · {t("label.logic")}: {analyzer.logicVersion}</>
          )}
        </p>
      )}
      <p className="ai-muted" style={{ margin: "4px 0", fontSize: 13 }}>
        {t("label.decisions")}: {analyzer.decisionCount}
      </p>
    </div>
  );
}
