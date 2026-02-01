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
      <div className="ai-card ai-card--error" role="alert">
        <strong>Error:</strong> {message}
        {errorKind === "HTTP_ERROR" && httpStatus != null && (
          <span className="ai-muted" style={{ display: "block", marginTop: 6 }}>
            HTTP {httpStatus}
            {detail != null && detail !== "" ? ` — ${detail}` : ""}
          </span>
        )}
        {hasDebug && onCopyDebug && (
          <button
            type="button"
            className="ai-btn ai-btn--accent"
            style={{ marginTop: 10 }}
            onClick={onCopyDebug}
          >
            Copy debug info
          </button>
        )}
      </div>
    </div>
  );
}
