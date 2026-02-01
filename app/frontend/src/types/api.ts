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
