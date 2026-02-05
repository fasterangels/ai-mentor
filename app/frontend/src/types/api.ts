/** API response types for decision-support backend */

export interface HealthResponse {
  status: string;
}

export interface ResolverInput {
  home_text: string;
  away_text: string;
  kickoff_hint_utc?: string;
  window_hours?: number;
  competition_id?: string | null;
}

export interface ResolverOutput {
  status: "RESOLVED" | "AMBIGUOUS" | "NOT_FOUND";
  match_id: string | null;
  candidates: Array<{ match_id: string; kickoff_utc: string; competition_id: string }>;
  notes: string[];
}

export interface PipelineInput {
  match_id: string;
  domains: string[];
  window_hours?: number;
  force_refresh?: boolean;
}

export interface MarketDecision {
  market: string;
  decision: string;
  probabilities: Record<string, number>;
  separation: number;
  confidence: number;
  risk: number;
  reasons: string[];
}

export interface AnalyzerResult {
  status: "OK" | "NO_PREDICTION";
  analysis_run: { logic_version: string; flags: string[] };
  decisions: MarketDecision[];
}

export interface RunAnalysisRequest {
  competition_id: string | null;
  home_team_id: string;
  away_team_id: string;
  match_date: string;
  mode: "PREGAME" | "LIVE";
  markets: string[];
}

export interface RunAnalysisResponse {
  status: string;
  match_id: string;
  evidence_pack?: unknown;
  analyzer_result?: AnalyzerResult;
}

export interface KPIReport {
  period: string;
  reference_date_utc: string;
  total_predictions: number;
  hits: number;
  misses: number;
  hit_rate: number;
  miss_rate: number;
}

export interface HistoryRow {
  id: number;
  evaluated_at_utc: string;
  match_id: string;
  home_team: string;
  away_team: string;
  market: string;
  decision: string;
  final_home_score: number;
  final_away_score: number;
  hit: boolean;
}

export interface EvaluationHistoryResponse {
  items: HistoryRow[];
}

/** Request for POST /api/v1/pipeline/shadow/run (canonical analysis flow). */
export interface ShadowPipelineRequest {
  connector_name?: string;
  match_id: string;
  final_home_goals?: number;
  final_away_goals?: number;
  status?: string;
}

/** Pipeline report shape (decisions, evaluation, audit). */
export interface ShadowPipelineReport {
  ingestion?: { payload_checksum?: string | null; collected_at?: string | null };
  analysis?: {
    snapshot_id?: number | null;
    markets_picks_confidences?: Record<string, unknown>;
    decisions?: MarketDecision[];
  };
  resolution?: { market_outcomes?: Record<string, unknown> };
  evaluation_report_checksum?: string | null;
  proposal?: { diffs?: unknown[]; guardrails_results?: unknown[]; proposal_checksum?: string | null };
  audit?: {
    changed_count?: number;
    per_market_change_count?: Record<string, number>;
    snapshots_checksum?: string | null;
    current_policy_checksum?: string | null;
    proposed_policy_checksum?: string | null;
  };
  error?: string;
  detail?: string;
}
