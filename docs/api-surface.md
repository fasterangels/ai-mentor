# API Surface Contract

## Supported Entry Points
- `/pipeline/shadow/run` — **Supported**. Canonical pipeline execution (ingestion → analyze → attach result → evaluate → tuner → audit).

## Non-Supported / Deprecated Entry Points
- `/api/v1/analyze` — **Not supported by design**. /api/v1/analyze is intentionally not supported (501). Use /pipeline/shadow/run. Returns **501 Not Implemented** with error code `ANALYZE_ENDPOINT_NOT_SUPPORTED`. Hidden from OpenAPI/Swagger.

## UI Rule
- UI MUST call `/pipeline/shadow/run` and render: `decisions`, `evaluation`, `audit`.

## Rationale
- Deterministic, explainable analysis is only valid inside the pipeline execution model (snapshots, evaluation, audit).
