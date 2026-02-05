/**
 * Maps API response JSON to ResultVM. Defensive: never throws; returns valid ResultVM for any input.
 * BLOCK 8.7 — one function, typed view-model, null-safe.
 */
import type { ResultVM, ResolverVM, AnalyzerVM, EvidenceVM, EvaluationKPI } from "./types";

function safeStr(x: unknown): string {
  if (x == null) return "";
  if (typeof x === "string") return x.trim();
  return String(x).trim();
}

function safeArray<T>(x: unknown): T[] {
  return Array.isArray(x) ? (x as T[]) : [];
}

function safeNum(x: unknown): number | undefined {
  if (typeof x === "number" && !Number.isNaN(x)) return x;
  return undefined;
}

/** Best-effort resolver status from common API locations */
function resolveResolverStatus(api: Record<string, unknown>): string {
  const s =
    (api.resolver as Record<string, unknown> | undefined)?.status ??
    (api.result as Record<string, unknown> | undefined)?.resolver_status ??
    (api.resolution as Record<string, unknown> | undefined)?.status ??
    api.status;
  const str = safeStr(s).toUpperCase();
  if (str) return str;
  return "UNKNOWN";
}

/** Best-effort match_id from common locations */
function resolveMatchId(api: Record<string, unknown>): string | null {
  const raw =
    api.match_id ??
    (api.result as Record<string, unknown> | undefined)?.match_id ??
    (api.resolver as Record<string, unknown> | undefined)?.match_id;
  if (raw == null) return null;
  const s = safeStr(raw);
  return s || null;
}

/** Normalize evidence from multiple possible locations to EvidenceVM[] */
function normalizeEvidence(api: Record<string, unknown>): EvidenceVM[] {
  const sources: unknown[] = [];
  const evidence = api.evidence;
  const analysisEvidence = (api.analysis as Record<string, unknown> | undefined)?.evidence;
  const resultEvidence = (api.result as Record<string, unknown> | undefined)?.evidence;
  const evidencePack = api.evidence_pack;

  if (Array.isArray(evidence)) sources.push(...evidence);
  if (Array.isArray(analysisEvidence)) sources.push(...analysisEvidence);
  if (Array.isArray(resultEvidence)) sources.push(...resultEvidence);
  if (evidencePack != null && typeof evidencePack === "object") {
    const pack = evidencePack as Record<string, unknown>;
    if (pack.match_id != null)
      sources.push({ title: "match_id", detail: String(pack.match_id), source: "evidence_pack" });
    const domains = safeArray<string>(pack.domains);
    if (domains.length)
      sources.push({ title: "domains", detail: domains.join(", "), source: "evidence_pack" });
    if (pack.captured_at_utc != null)
      sources.push({
        title: "captured_at_utc",
        detail: String(pack.captured_at_utc),
        source: "evidence_pack",
      });
    const flags = safeArray<string>(pack.flags);
    if (flags.length)
      sources.push({ title: "flags", detail: flags.join(", "), tags: flags, source: "evidence_pack" });
  }

  const out: EvidenceVM[] = [];
  for (const item of sources) {
    if (item != null && typeof item === "object") {
      const o = item as Record<string, unknown>;
      out.push({
        title: safeStr(o.title ?? o.label ?? o.name) || "Evidence",
        detail: safeStr(o.detail ?? o.value ?? o.description ?? JSON.stringify(o)),
        source: safeStr(o.source) || undefined,
        confidence: o.confidence != null ? (typeof o.confidence === "number" ? o.confidence : safeStr(o.confidence)) : undefined,
        tags: Array.isArray(o.tags) ? (o.tags as string[]).map(String) : undefined,
      });
    }
  }
  return out;
}

/** Normalize notes to string[] */
function normalizeNotesList(api: Record<string, unknown>): string[] {
  const arr: string[] = [];
  const notes = api.notes ?? (api.result as Record<string, unknown> | undefined)?.notes;
  const resolverNotes = (api.resolver as Record<string, unknown> | undefined)?.notes;
  if (Array.isArray(notes)) notes.forEach((n) => arr.push(safeStr(n)));
  if (Array.isArray(resolverNotes)) resolverNotes.forEach((n) => arr.push(safeStr(n)));
  return arr.filter(Boolean);
}

/** Normalize warnings to string[] */
function normalizeWarningsList(api: Record<string, unknown>): string[] {
  const arr: string[] = [];
  const warnings = api.warnings ?? (api.meta as Record<string, unknown> | undefined)?.warnings;
  if (Array.isArray(warnings)) warnings.forEach((w) => arr.push(safeStr(w)));
  return arr.filter(Boolean);
}

/** Best-effort evaluation KPIs from evaluation_v2, analyzer.analysis_run (flags, counts, conflict_summary). Never throws. */
function normalizeEvaluation(api: Record<string, unknown>): EvaluationKPI[] {
  const out: EvaluationKPI[] = [];

  try {
    const evaluationV2 = api.evaluation_v2 as Record<string, unknown> | undefined;
    if (evaluationV2 != null && typeof evaluationV2 === "object") {
      const checksum = evaluationV2.evaluation_report_checksum;
      if (checksum != null && typeof checksum === "string" && checksum.length > 0) {
        out.push({
          label: "Evaluation checksum",
          value: checksum.length > 12 ? `${checksum.slice(0, 12)}…` : checksum,
          source: "evaluation_v2",
        });
      }
      const runtimeMs = safeNum(evaluationV2.analyzer_runtime_ms);
      if (runtimeMs != null) {
        out.push({
          label: "Analyzer runtime",
          value: runtimeMs,
          unit: "ms",
          source: "evaluation_v2",
        });
      }
      const outputHash = evaluationV2.output_hash;
      if (outputHash != null && typeof outputHash === "string" && outputHash.length > 0) {
        out.push({
          label: "Output hash",
          value: outputHash.length > 12 ? `${outputHash.slice(0, 12)}…` : outputHash,
          source: "evaluation_v2",
        });
      }
      const stability = evaluationV2.stability as Record<string, unknown> | undefined;
      if (stability != null && typeof stability === "object") {
        const stable = stability.stable;
        if (stable !== undefined) {
          out.push({
            label: "Stable",
            value: stable === true ? "Yes" : "No",
            source: "evaluation_v2",
          });
        }
        const guardrailTriggered = stability.guardrail_triggered;
        if (guardrailTriggered !== undefined) {
          out.push({
            label: "Guardrail triggered",
            value: guardrailTriggered === true ? "Yes" : "No",
            source: "evaluation_v2",
          });
        }
      }
    }

    const analyzer = api.analyzer as Record<string, unknown> | undefined;
    const analysisRun =
      (analyzer != null && typeof analyzer === "object" ? analyzer.analysis_run : undefined) as
        | Record<string, unknown>
        | undefined;
    if (analysisRun != null && typeof analysisRun === "object") {
      const counts = analysisRun.counts as Record<string, unknown> | undefined;
      if (counts != null && typeof counts === "object") {
        const play = safeNum(counts.PLAY);
        const noBet = safeNum(counts.NO_BET);
        const noPred = safeNum(counts.NO_PREDICTION);
        if (play != null) out.push({ label: "PLAY", value: play, source: "analyzer.analysis_run.counts" });
        if (noBet != null) out.push({ label: "NO_BET", value: noBet, source: "analyzer.analysis_run.counts" });
        if (noPred != null)
          out.push({ label: "NO_PREDICTION", value: noPred, source: "analyzer.analysis_run.counts" });
      }
      const flags = safeArray<string>(analysisRun.flags);
      if (flags.length > 0) {
        out.push({
          label: "Flags",
          value: flags.join(", "),
          source: "analyzer.analysis_run.flags",
        });
      }
      const conflictSummary = analysisRun.conflict_summary as Record<string, unknown> | undefined;
      if (conflictSummary != null && typeof conflictSummary === "object") {
        const eq = safeNum(conflictSummary.evidence_quality);
        const cq = safeNum(conflictSummary.consensus_quality);
        if (eq != null) {
          out.push({
            label: "Evidence quality",
            value: eq,
            source: "analyzer.analysis_run.conflict_summary",
          });
        }
        if (cq != null) {
          out.push({
            label: "Consensus quality",
            value: cq,
            source: "analyzer.analysis_run.conflict_summary",
          });
        }
      }
    }
  } catch {
    // Mapper must never throw; leave out empty
  }

  return out;
}

/** Determine analyzer outcome: PREDICTION_AVAILABLE vs NO_PREDICTION */
function resolveAnalyzerOutcome(api: Record<string, unknown>): string {
  const analyzer = api.analyzer as Record<string, unknown> | undefined;
  const analysis = api.analysis as Record<string, unknown> | undefined;
  const outcomeRaw = analyzer?.outcome ?? analysis?.outcome ?? analyzer?.status ?? api.status;
  const outcomeStr = safeStr(outcomeRaw).toUpperCase();

  if (/NO_PREDICTION|NO_BET|NO_DECISION/i.test(outcomeStr)) return "NO_PREDICTION";
  const predictions = api.predictions ?? analyzer?.predictions ?? analysis?.predictions;
  const markets = api.markets ?? analyzer?.decisions ?? analysis?.decisions;
  const hasPredictions = Array.isArray(predictions) && predictions.length > 0;
  const hasMarkets = Array.isArray(markets) && markets.length > 0;
  if (hasPredictions || hasMarkets) return "PREDICTION_AVAILABLE";
  if (outcomeStr === "OK" || outcomeStr === "PREDICTION_AVAILABLE") return "PREDICTION_AVAILABLE";
  if (outcomeStr) return outcomeStr;
  return "UNKNOWN";
}

/**
 * Maps API response (any JSON) to ResultVM. Never throws.
 */
export function mapApiToResultVM(
  apiJson: unknown,
  options?: { homeTeam?: string; awayTeam?: string }
): ResultVM {
  const homeTeam = options?.homeTeam ?? "";
  const awayTeam = options?.awayTeam ?? "";

  if (apiJson == null || typeof apiJson !== "object" || Array.isArray(apiJson)) {
    return {
      matchId: null,
      homeTeam,
      awayTeam,
      resolver: { status: "UNKNOWN", matchId: null, notes: [] },
      analyzer: { outcome: "NO_PREDICTION", statusLabel: "", logicVersion: null, decisionCount: 0 },
      evidence: [],
      notes: [],
      warnings: [],
    };
  }

  const api = apiJson as Record<string, unknown>;
  const resolver = (api.resolver ?? {}) as Record<string, unknown>;
  const analyzer = (api.analyzer ?? {}) as Record<string, unknown>;
  const analysisRun = (analyzer.analysis_run ?? {}) as Record<string, unknown>;
  const decisions = safeArray(analyzer.decisions);

  const resolverStatus = resolveResolverStatus(api);
  const matchId = resolveMatchId(api);
  const resolverNotes = safeArray<string>(resolver.notes);
  const notesList = normalizeNotesList(api);
  const warningsList = normalizeWarningsList(api);

  const resolverVM: ResolverVM = {
    status: resolverStatus,
    matchId,
    notes: resolverNotes.length > 0 ? resolverNotes : notesList,
  };

  const outcome = resolveAnalyzerOutcome(api);
  const statusLabel = safeStr(analyzer.status ?? api.status);
  const logicVersion = safeStr(analysisRun.logic_version) || null;

  const analyzerVM: AnalyzerVM = {
    outcome,
    statusLabel: statusLabel || (outcome === "NO_PREDICTION" ? "NO_PREDICTION" : "OK"),
    logicVersion,
    decisionCount: decisions.length,
  };

  const evidence = normalizeEvidence(api);
  const evaluation = normalizeEvaluation(api);

  return {
    matchId,
    homeTeam,
    awayTeam,
    resolver: resolverVM,
    analyzer: analyzerVM,
    evidence,
    notes: notesList,
    warnings: warningsList,
    evaluation: evaluation.length > 0 ? evaluation : undefined,
  };
}
