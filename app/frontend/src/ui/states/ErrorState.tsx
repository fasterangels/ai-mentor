/**
 * BLOCK 8.8: Error state — deterministic messages by error kind.
 */
import type { ErrorKind } from "./stateMachine";

export interface ErrorStateProps {
  errorKind: ErrorKind;
  httpStatus?: number | null;
  detail?: string | null;
  onCopyDebug?: () => void;
  hasDebug?: boolean;
}

const MESSAGES: Record<ErrorKind, string> = {
  NETWORK_ERROR: "Backend unreachable. Check that the service is running.",
  HTTP_ERROR: "Request failed. See status and detail below.",
  RESOLVER_NOT_FOUND: "Match not found in kickoff window.",
  RESOLVER_AMBIGUOUS: "Match could not be resolved uniquely.",
  ANALYZER_NO_PREDICTION: "No prediction available for this match.",
};

export default function ErrorState({
  errorKind,
  httpStatus,
  detail,
  onCopyDebug,
  hasDebug,
}: ErrorStateProps) {
  const message = MESSAGES[errorKind];

  return (
    <div className="ai-section">
      <div className="ai-card ai-card--error ai-empty-state" role="alert">
        <div className="ai-empty-state__icon" style={{ color: "var(--error)" }}>
          <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="12" cy="12" r="10" />
            <line x1="12" y1="8" x2="12" y2="12" />
            <line x1="12" y1="16" x2="12.01" y2="16" />
          </svg>
        </div>
        <div style={{ textAlign: "center" }}>
          <strong style={{ display: "block", marginBottom: 6 }}>Error</strong>
          <p className="ai-empty-state__text" style={{ margin: "0 0 8px" }}>{message}</p>
          {errorKind === "HTTP_ERROR" && httpStatus != null && (
            <span className="ai-muted" style={{ display: "block", fontSize: "0.8125rem" }}>
              HTTP {httpStatus}
              {detail != null && detail !== "" ? ` — ${detail}` : ""}
            </span>
          )}
          {hasDebug && onCopyDebug && (
            <button
              type="button"
              className="ai-btn ai-btn--accent"
              style={{ marginTop: 12 }}
              onClick={onCopyDebug}
              aria-label="Copy debug info"
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ marginRight: 6, verticalAlign: "middle" }}>
                <rect x="9" y="9" width="13" height="13" rx="2" ry="2" />
                <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
              </svg>
              Copy debug info
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
