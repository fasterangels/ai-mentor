/**
 * BLOCK 8.8: Empty result state — shown above ResultView when RESULT has emptyKind.
 */
import type { EmptyKind } from "./stateMachine";

export interface EmptyResultStateProps {
  emptyKind: EmptyKind;
}

const MESSAGES: Record<EmptyKind, string> = {
  RESOLVER_NOT_FOUND: "Match not found in kickoff window.",
  RESOLVER_AMBIGUOUS: "Match could not be resolved uniquely.",
  ANALYZER_NO_PREDICTION: "No prediction available for this match.",
};

export default function EmptyResultState({ emptyKind }: EmptyResultStateProps) {
  const message = MESSAGES[emptyKind];
  return (
    <div className="ai-section">
      <div className="ai-card ai-card--warning" role="status">
        <p className="ai-muted" style={{ margin: 0, fontSize: 14 }}>{message}</p>
      </div>
    </div>
  );
}
