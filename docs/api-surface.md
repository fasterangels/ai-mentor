# API Surface Contract

## Supported Entry Points
- `/pipeline/shadow/run` — **Supported**. Canonical pipeline execution (ingestion → analyze → attach result → evaluate → tuner → audit). Phase A completion note: [docs/phase-a-complete.md](phase-a-complete.md).

## Non-Supported / Deprecated Entry Points
- `/api/v1/analyze` — **Not supported by design**. /api/v1/analyze is intentionally not supported (501). Use /pipeline/shadow/run. Returns **501 Not Implemented** with error code `ANALYZE_ENDPOINT_NOT_SUPPORTED`. Hidden from OpenAPI/Swagger.

## UI Rule
- UI MUST call `/pipeline/shadow/run` and render: `decisions`, `evaluation`, `audit`.

## Pipeline report schema versioning
- Every pipeline report (success or error) includes:
  - **`schema_version`**: `"report.v1"` — contract version for the report payload shape.
  - **`canonical_flow`**: `"/pipeline/shadow/run"` — identifies the supported flow; UI can refuse unsupported flows deterministically.
  - **`generated_at`**: ISO timestamp; **`app_version`**: from repo `VERSION` file (when available).
- **Strict validation**: Set `REPORT_SCHEMA_VALIDATE_STRICT=true` (or `1`/`yes`) to fail the pipeline when the report fails schema validation (required keys, allowed `schema_version`). Default is `false` (warn-only / no fail). Use in CI or dev to ensure report contract is met.
