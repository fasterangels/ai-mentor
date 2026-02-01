/** Evaluation API: KPIs and prediction history. */

import { apiGet } from "./client";
import type { KPIReport, EvaluationHistoryResponse } from "@/types/api";

export async function getKpis(
  period: "DAY" | "WEEK" | "MONTH",
  referenceDateUtc: string
): Promise<KPIReport> {
  return apiGet<KPIReport>(
    `/api/v1/evaluation/kpis?period=${period}&reference_date_utc=${encodeURIComponent(referenceDateUtc)}`
  );
}

export async function getPredictionHistory(params: {
  from?: string;
  to?: string;
  filter?: "all" | "hits" | "misses";
}): Promise<EvaluationHistoryResponse> {
  const q = new URLSearchParams();
  if (params.from) q.set("from", params.from);
  if (params.to) q.set("to", params.to);
  if (params.filter) q.set("filter", params.filter);
  return apiGet<EvaluationHistoryResponse>(`/api/v1/evaluation/history?${q.toString()}`);
}
