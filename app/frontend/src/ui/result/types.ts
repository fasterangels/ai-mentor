/** View-model types for canonical Result View (BLOCK 8.7). UI depends on these, not raw API shape. */

export type ResolverStatus =
  | "RESOLVED"
  | "AMBIGUOUS"
  | "NOT_FOUND"
  | string;

export type AnalyzerOutcome =
  | "PREDICTION_AVAILABLE"
  | "NO_PREDICTION"
  | string;

export interface ResolverVM {
  status: ResolverStatus;
  matchId: string | null;
  notes: string[];
}

export interface AnalyzerVM {
  outcome: AnalyzerOutcome;
  statusLabel: string;
  logicVersion: string | null;
  decisionCount: number;
}

export interface EvidenceVM {
  title: string;
  detail: string;
  source?: string;
  confidence?: number | string;
  tags?: string[];
}

/** Single evaluation KPI for read-only display (BLOCK 1). */
export interface EvaluationKPI {
  label: string;
  value: string | number;
  unit?: string;
  source?: string;
}

export interface ResultVM {
  matchId: string | null;
  homeTeam: string;
  awayTeam: string;
  resolver: ResolverVM;
  analyzer: AnalyzerVM;
  evidence: EvidenceVM[];
  notes: string[];
  warnings: string[];
  /** Read-only KPIs from evaluation_v2 / analyzer.analysis_run; empty if none. */
  evaluation?: EvaluationKPI[];
}
