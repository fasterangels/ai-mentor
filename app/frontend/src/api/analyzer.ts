/** Analyzer API: run analysis (resolver + pipeline + analyzer).
 * Note: /api/v1/analyze is intentionally not supported (501). Use /pipeline/shadow/run for canonical analysis.
 */

import { apiPost } from "./client";
import type { RunAnalysisRequest, RunAnalysisResponse } from "@/types/api";

export async function runAnalysis(
  body: RunAnalysisRequest
): Promise<RunAnalysisResponse> {
  return apiPost<RunAnalysisResponse>("/api/v1/analyze", body);
}
