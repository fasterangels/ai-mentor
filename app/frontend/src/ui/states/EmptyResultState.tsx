/**
 * BLOCK 8.8: Empty result state — shown above ResultView when RESULT has emptyKind.
 */
import { t } from "../../i18n";
import type { EmptyKind } from "./stateMachine";

const EMPTY_KEYS: Record<EmptyKind, string> = {
  RESOLVER_NOT_FOUND: "error.resolver_not_found",
  RESOLVER_AMBIGUOUS: "error.resolver_ambiguous",
  ANALYZER_NO_PREDICTION: "error.analyzer_no_prediction",
};

export interface EmptyResultStateProps {
  emptyKind: EmptyKind;
}

const MESSAGES: Record<EmptyKind, { icon: React.ReactNode }> = {
  RESOLVER_NOT_FOUND: {
    icon: (
      <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
        <circle cx="11" cy="11" r="8" />
        <line x1="21" y1="21" x2="16.65" y2="16.65" />
        <line x1="8" y1="11" x2="14" y2="11" />
      </svg>
    ),
  },
  RESOLVER_AMBIGUOUS: {
    icon: (
      <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
        <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
        <line x1="12" y1="9" x2="12" y2="13" />
        <line x1="12" y1="17" x2="12.01" y2="17" />
      </svg>
    ),
  },
  ANALYZER_NO_PREDICTION: {
    icon: (
      <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
        <circle cx="12" cy="12" r="10" />
        <line x1="15" y1="9" x2="9" y2="15" />
        <line x1="9" y1="9" x2="15" y2="15" />
      </svg>
    ),
  },
};

export default function EmptyResultState({ emptyKind }: EmptyResultStateProps) {
  const { icon } = MESSAGES[emptyKind];
  const text = t(EMPTY_KEYS[emptyKind]);
  return (
    <div className="ai-section">
      <div className="ai-card ai-card--warning ai-empty-state" role="status">
        <div className="ai-empty-state__icon" style={{ color: "var(--warning)" }}>
          {icon}
        </div>
        <p className="ai-empty-state__text">{text}</p>
      </div>
    </div>
  );
}
