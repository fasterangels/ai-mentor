import type { ResultVM } from "./types";
import MatchHeader from "./MatchHeader";
import ResolverStatusCard from "./ResolverStatusCard";
import AnalyzerOutcomeCard from "./AnalyzerOutcomeCard";
import EvaluationPanel from "./EvaluationPanel";
import EvidenceList from "./EvidenceList";
import NotesPanel from "./NotesPanel";

export interface ResultViewProps {
  vm: ResultVM;
  /** BLOCK 2: Called when Export is clicked; only shown when provided. Export disabled unless RESULT (ResultView is only rendered when RESULT). */
  onExport?: (vm: ResultVM) => void;
}

/**
 * Canonical Result View (BLOCK 8.7). Renders structured result from view-model.
 * Layout: MatchHeader + Export → Resolver + Analyzer cards → Evaluation → Evidence → Notes.
 */
export default function ResultView({ vm, onExport }: ResultViewProps) {
  return (
    <>
      <div className="ai-section" style={{ display: "flex", flexWrap: "wrap", alignItems: "flex-start", gap: "var(--s-3)" }}>
        <div style={{ flex: "1 1 280px", minWidth: 0 }}>
          <MatchHeader vm={vm} />
        </div>
        {onExport != null && (
          <div style={{ alignSelf: "center" }}>
            <button
              type="button"
              className="ai-btn ai-btn--ghost"
              onClick={() => onExport(vm)}
              aria-label="Export result (PDF/summary)"
            >
              Export
            </button>
          </div>
        )}
      </div>

      <div
        className="ai-section"
        style={{
          display: "flex",
          flexWrap: "wrap",
          gap: "var(--s-3)",
          alignItems: "stretch",
        }}
      >
        <ResolverStatusCard resolver={vm.resolver} />
        <AnalyzerOutcomeCard analyzer={vm.analyzer} />
      </div>

      <EvaluationPanel items={vm.evaluation} />
      <EvidenceList items={vm.evidence} />
      <NotesPanel notes={vm.notes} warnings={vm.warnings} />
    </>
  );
}
