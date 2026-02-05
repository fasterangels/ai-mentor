# API Surface Contract

## Supported Entry Points

- **/pipeline/shadow/run** — Supported. Canonical pipeline execution.

## Non-Supported / Deprecated Entry Points

- **/api/v1/analyze** — Not supported by design. Returns 501 with code `ANALYZE_ENDPOINT_NOT_SUPPORTED`. Hidden from OpenAPI/Swagger.

## UI Rule

- UI MUST call `/pipeline/shadow/run` and map output sections: decisions, evaluation, audit.

## Rationale

- Deterministic, explainable analysis is only valid inside the pipeline execution model (snapshots, evaluation, audit).
