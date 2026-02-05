/**
 * Canonical analysis: POST /api/v1/pipeline/shadow/run only.
 * /api/v1/analyze is not supported (501). Use runShadowPipeline + pipelineReportToAnalyzeResponse.
 */

export {
  runShadowPipeline,
  pipelineReportToAnalyzeResponse,
  type ShadowPipelineRequest,
  type ShadowPipelineReport,
  type AnalyzeResponseFromPipeline,
} from "./pipeline";
