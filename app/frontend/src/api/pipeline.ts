/**
 * Canonical analysis: POST /api/v1/pipeline/shadow/run only.
 * Maps pipeline report to the UI's AnalyzeResponse shape (decisions, evaluation, audit).
 */

import { apiPost } from "./client";
import type {
  ShadowPipelineRequest,
  ShadowPipelineReport,
  MarketDecision,
} from "@/types/api";

export type { ShadowPipelineRequest, ShadowPipelineReport };

/** Run shadow pipeline (single supported flow). In Tauri, uses invoke to bypass fetch/CORS. */
export async function runShadowPipeline(
  body: ShadowPipelineRequest
): Promise<ShadowPipelineReport> {
  const payload = {
    connector_name: body.connector_name ?? "sample_platform",
    match_id: body.match_id,
    final_home_goals: body.final_home_goals ?? 0,
    final_away_goals: body.final_away_goals ?? 0,
    status: body.status ?? "FINAL",
  };

  if (typeof window !== "undefined" && "__TAURI__" in window) {
    const { invoke } = await import("@tauri-apps/api/core");
    const raw = await invoke("shadow_run", { payload });
    if (raw != null && typeof raw === "object") return raw as ShadowPipelineReport;
    throw new Error("PIPELINE_INVALID_DATA");
  }

  return apiPost<ShadowPipelineReport>("/api/v1/pipeline/shadow/run", payload);
}

/** UI-facing response shape (matches existing result view). */
export interface AnalyzeResponseFromPipeline {
  status: string;
  match_id: string;
  resolver: { status: string; match_id: string };
  analyzer: {
    status: string;
    analysis_run?: { logic_version: string; flags: string[] };
    decisions: MarketDecision[];
  };
  evaluation_v2?: {
    evaluation_report_checksum?: string | null;
    proposal_checksum?: string | null;
  };
  evidence_pack?: { match_id?: string; domains?: string[] };
  audit?: ShadowPipelineReport["audit"];
}

/**
 * Map pipeline report to UI AnalyzeResponse. Never throws.
 */
export function pipelineReportToAnalyzeResponse(
  report: ShadowPipelineReport,
  matchId: string
): AnalyzeResponseFromPipeline {
  const safe: AnalyzeResponseFromPipeline = {
    status: "ERROR",
    match_id: matchId,
    resolver: { status: "UNKNOWN", match_id: matchId },
    analyzer: { status: "UNKNOWN", decisions: [] },
  };
  if (report == null || typeof report !== "object") return safe;
  if (report.error) {
    return {
      status: "ERROR",
      match_id: matchId,
      resolver: { status: "UNKNOWN", match_id: matchId },
      analyzer: { status: report.error, decisions: [] },
    };
  }
  const decisions: MarketDecision[] = Array.isArray(report.analysis?.decisions)
    ? (report.analysis.decisions as MarketDecision[])
    : [];
  const evaluationV2 =
    report.evaluation_report_checksum != null || report.proposal != null
      ? {
          evaluation_report_checksum: report.evaluation_report_checksum ?? undefined,
          proposal_checksum:
            (report.proposal as { proposal_checksum?: string })?.proposal_checksum ?? undefined,
        }
      : undefined;
  return {
    status: "OK",
    match_id: matchId,
    resolver: { status: "RESOLVED", match_id: matchId },
    analyzer: {
      status: decisions.length > 0 ? "OK" : "NO_PREDICTION",
      analysis_run: { logic_version: "v2", flags: [] },
      decisions,
    },
    evaluation_v2: evaluationV2,
    evidence_pack: report.ingestion
      ? { match_id: matchId, domains: ["pipeline"] }
      : undefined,
    audit: report.audit,
  };
}
