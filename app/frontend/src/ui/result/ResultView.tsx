import type { ResultVM } from "./types";
import MatchHeader from "./MatchHeader";
import ResolverStatusCard from "./ResolverStatusCard";
import AnalyzerOutcomeCard from "./AnalyzerOutcomeCard";
import EvaluationPanel from "./EvaluationPanel";
import EvidenceList from "./EvidenceList";
import NotesPanel from "./NotesPanel";

export interface ResultViewProps {
  vm: ResultVM;
}

/**
 * Canonical Result View (BLOCK 8.7). Renders structured result from view-model.
 * Layout: MatchHeader → Resolver + Analyzer cards (side-by-side on wide, stacked on narrow) → Evidence → Notes.
 */
export default function ResultView({ vm }: ResultViewProps) {
  return (
    <>
      <MatchHeader vm={vm} />

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
