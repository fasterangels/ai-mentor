/**
 * BLOCK 8.8: UI state machine for analyze flow.
 * Deterministic mapping from (loading, error, result, httpStatus, result body) to UI state.
 */

export type AnalyzeUIState = "IDLE" | "ANALYZING" | "RESULT" | "ERROR";

export type ErrorKind =
  | "NETWORK_ERROR"
  | "HTTP_ERROR"
  | "RESOLVER_NOT_FOUND"
  | "RESOLVER_AMBIGUOUS"
  | "ANALYZER_NO_PREDICTION";

/** Empty result reason (RESULT state with special empty messaging). */
export type EmptyKind =
  | "RESOLVER_NOT_FOUND"
  | "RESOLVER_AMBIGUOUS"
  | "ANALYZER_NO_PREDICTION";

export interface AnalyzeUIStateResult {
  state: AnalyzeUIState;
  errorKind?: ErrorKind;
  emptyKind?: EmptyKind;
}

function safeStr(x: unknown): string {
  if (x == null) return "";
  if (typeof x === "string") return x.trim();
  return String(x).trim();
}

function getResolverStatus(result: Record<string, unknown>): string {
  const s =
    (result.resolver as Record<string, unknown> | undefined)?.status ??
    (result.result as Record<string, unknown> | undefined)?.resolver_status ??
    result.status;
  return safeStr(s).toUpperCase();
}

function getAnalyzerOutcome(result: Record<string, unknown>): string {
  const analyzer = result.analyzer as Record<string, unknown> | undefined;
  const analysis = result.analysis as Record<string, unknown> | undefined;
  const outcome =
    safeStr(analyzer?.outcome ?? analysis?.outcome ?? analyzer?.status ?? result.status).toUpperCase();
  if (/NO_PREDICTION|NO_BET|NO_DECISION/i.test(outcome)) return "NO_PREDICTION";
  const decisions = Array.isArray(analyzer?.decisions) ? analyzer.decisions : [];
  const predictions = result.predictions ?? analyzer?.predictions ?? analysis?.predictions;
  if (decisions.length > 0) return "PREDICTION_AVAILABLE";
  if (Array.isArray(predictions) && predictions.length > 0) return "PREDICTION_AVAILABLE";
  return outcome || "UNKNOWN";
}

/**
 * Returns current UI state and optional error/empty kind.
 * - Fetch throws → ERROR, errorKind NETWORK_ERROR (caller sets errorKind).
 * - HTTP status >= 400 → ERROR, errorKind HTTP_ERROR (caller sets errorKind).
 * - Result with resolver NOT_FOUND → RESULT, emptyKind RESOLVER_NOT_FOUND.
 * - Result with resolver AMBIGUOUS → RESULT, emptyKind RESOLVER_AMBIGUOUS.
 * - Result with analyzer NO_PREDICTION → RESULT, emptyKind ANALYZER_NO_PREDICTION.
 * - Otherwise RESULT with no emptyKind.
 */
export function getAnalyzeUIState(
  loading: boolean,
  errorMessage: string | null,
  httpStatus: number | null,
  result: Record<string, unknown> | null,
  errorKind?: ErrorKind
): AnalyzeUIStateResult {
  if (loading) return { state: "ANALYZING" };
  if (errorMessage != null && errorMessage !== "" && result == null) {
    return { state: "ERROR", errorKind: errorKind ?? "HTTP_ERROR" };
  }
  if (result != null && typeof result === "object") {
    const resolverStatus = getResolverStatus(result);
    const analyzerOutcome = getAnalyzerOutcome(result);
    if (resolverStatus === "NOT_FOUND")
      return { state: "RESULT", emptyKind: "RESOLVER_NOT_FOUND" };
    if (resolverStatus === "AMBIGUOUS")
      return { state: "RESULT", emptyKind: "RESOLVER_AMBIGUOUS" };
    if (analyzerOutcome === "NO_PREDICTION")
      return { state: "RESULT", emptyKind: "ANALYZER_NO_PREDICTION" };
    return { state: "RESULT" };
  }
  return { state: "IDLE" };
}
