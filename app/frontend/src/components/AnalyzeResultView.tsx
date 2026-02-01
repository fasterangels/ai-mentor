
// Safe access helpers
function safeArray<T>(x: unknown): T[] {
  return Array.isArray(x) ? (x as T[]) : [];
}

function safeStringify(value: unknown): string {
  try {
    return JSON.stringify(value, null, 2);
  } catch {
    return String(value);
  }
}

function na(value: unknown): string {
  if (value === undefined || value === null) return "N/A";
  if (typeof value === "string" && value.trim() === "") return "N/A";
  return String(value);
}

/** Detect if result indicates no prediction (for explanation block) */
function isNoPrediction(result: Record<string, unknown> | null | undefined): boolean {
  if (!result || typeof result !== "object") return false;
  const top = (result.status ?? "").toString().toUpperCase();
  const resolverStatus = (result.resolver?.status ?? "").toString().toUpperCase();
  const analyzerStatus = (result.analyzer?.status ?? "").toString().toUpperCase();
  if (["NO_PREDICTION", "NOT_FOUND", "AMBIGUOUS"].includes(top)) return true;
  if (["NOT_FOUND", "AMBIGUOUS"].includes(resolverStatus)) return true;
  if (analyzerStatus === "NO_PREDICTION") return true;
  const flags = safeArray<string>(result.flags).concat(
    safeArray<string>(result.analyzer?.analysis_run?.flags)
  );
  if (flags.some((f) => /NO_PREDICTION|NO_BET|NO_DECISION/i.test(String(f)))) return true;
  const decisions = safeArray(result.analyzer?.decisions);
  if (decisions.some((d) => /NO_PREDICTION|NO_BET|NO_DECISION/i.test(String(d?.decision ?? ""))))
    return true;
  return false;
}

function getNoPredictionMessage(result: Record<string, unknown> | null | undefined): string {
  if (!result) return "Not available";
  const resolverStatus = (result.resolver?.status ?? "").toString().toUpperCase();
  const top = (result.status ?? "").toString().toUpperCase();
  if (resolverStatus === "AMBIGUOUS" || top === "AMBIGUOUS")
    return "AMBIGUOUS: ο αγώνας δεν επιλύθηκε μονοσήμαντα.";
  if (resolverStatus === "NOT_FOUND" || top === "NOT_FOUND")
    return "NOT_FOUND: δεν βρέθηκε αγώνας στο παράθυρο kickoff.";
  if (top === "NO_PREDICTION")
    return "NO_PREDICTION: δεν υπάρχουν αρκετά αξιόπιστα δεδομένα/σήματα.";
  return "NO_PREDICTION: δεν υπάρχουν αρκετά αξιόπιστα δεδομένα/σήματα.";
}

export interface AnalyzeResultViewProps {
  result: Record<string, unknown> | null | undefined;
}

export default function AnalyzeResultView({ result }: AnalyzeResultViewProps) {
  if (!result || typeof result !== "object") {
    return (
      <div className="ai-section">
        <div className="ai-card">
          <p className="ai-muted">No result data.</p>
        </div>
      </div>
    );
  }

  const resolver = result.resolver ?? {};
  const matchId = result.match_id ?? resolver.match_id ?? null;
  const notes = safeArray<string>(resolver.notes).concat(safeArray<string>(result.notes));
  const evidencePack = result.evidence_pack;
  const analyzer = result.analyzer ?? {};
  const analysisRun = analyzer.analysis_run ?? {};
  const decisions = safeArray(analyzer.decisions);
  const noPred = isNoPrediction(result);
  const noPredMessage = getNoPredictionMessage(result);

  // Evidence items: domains, match_id, captured_at_utc, flags
  const evidenceItems: { label: string; value: string }[] = [];
  if (evidencePack && typeof evidencePack === "object") {
    if (evidencePack.match_id != null) evidenceItems.push({ label: "match_id", value: na(evidencePack.match_id) });
    const domains = safeArray<string>(evidencePack.domains);
    if (domains.length) evidenceItems.push({ label: "domains", value: domains.join(", ") });
    if (evidencePack.captured_at_utc != null)
      evidenceItems.push({ label: "captured_at_utc", value: na(evidencePack.captured_at_utc) });
    const epFlags = safeArray<string>(evidencePack.flags);
    if (epFlags.length) evidenceItems.push({ label: "flags", value: epFlags.join(", ") });
  }

  return (
    <>
      {/* 1) Resolver */}
      <div className="ai-section">
        <div className="ai-card">
          <div className="ai-cardHeader">
            <div className="ai-cardTitle">Resolver</div>
          </div>
          <p style={{ margin: "4px 0" }}>
            Status: {na(resolver.status)} · Match ID: {na(matchId)}
          </p>
          {notes.length > 0 && (
            <ul style={{ margin: "8px 0 0 0", paddingLeft: 20 }}>
              {notes.map((n, i) => (
                <li key={i}>{String(n)}</li>
              ))}
            </ul>
          )}
        </div>
      </div>

      {/* 2) Evidence Pack */}
      <div className="ai-section">
        <div className="ai-card">
          <div className="ai-cardHeader">
            <div className="ai-cardTitle">Evidence Pack</div>
          </div>
          {evidenceItems.length > 0 ? (
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 14 }}>
              <tbody>
                {evidenceItems.map((item, i) => (
                  <tr key={i} style={{ borderBottom: "1px solid var(--border)" }}>
                    <td style={{ padding: "6px 12px 6px 0", fontWeight: 500, width: "30%" }}>{item.label}</td>
                    <td style={{ padding: 6 }}>{item.value}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <p className="ai-muted" style={{ margin: 0 }}>No evidence data</p>
          )}
        </div>
      </div>

      {/* 3) Analyzer Decision */}
      <div className="ai-section">
        <div className="ai-card">
          <div className="ai-cardHeader">
            <div className="ai-cardTitle">Analyzer Decision</div>
          </div>
          <p style={{ margin: "4px 0" }}>
            Status: {na(analyzer.status)}
            {analysisRun.logic_version != null && ` · Logic: ${na(analysisRun.logic_version)}`}
          </p>
          {safeArray<string>(analysisRun.flags).length > 0 && (
            <p style={{ margin: "4px 0", fontSize: 14 }}>
              Flags: {safeArray<string>(analysisRun.flags).join(", ")}
            </p>
          )}
          {decisions.length > 0 && (
            <p className="ai-muted" style={{ margin: "8px 0 0 0", fontSize: 13 }}>
              {decisions.length} decision(s): {decisions.map((d: Record<string, unknown>) => (d?.decision ?? "—") as string).join(", ")}
            </p>
          )}
          {decisions.length === 0 && analyzer.status == null && (
            <p className="ai-muted" style={{ margin: 0 }}>Not available</p>
          )}
        </div>
      </div>

      {/* 4) NO_PREDICTION — valid outcome, not an error (BLOCK 8.7) */}
      {noPred && (
        <div className="ai-section">
          <div className="ai-card ai-card--warning">
            <p style={{ margin: "0 0 6px 0" }}>No valid prediction for this match.</p>
            <p className="ai-muted" style={{ margin: 0, fontSize: 14 }}>{noPredMessage}</p>
          </div>
        </div>
      )}

      {/* 5) Show raw JSON toggle (collapsed by default) */}
      <div className="ai-section">
        <div className="ai-card">
          <details>
            <summary className="ai-summary">Show raw JSON</summary>
            <pre className="ai-pre ai-mono" style={{ marginTop: 8 }}>{safeStringify(result)}</pre>
          </details>
        </div>
      </div>
    </>
  );
}
