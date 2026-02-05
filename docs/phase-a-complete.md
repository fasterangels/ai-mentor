# Phase A Complete — API Surface Cleanup

## What changed
- `/api/v1/analyze` is intentionally not supported and returns **501** with a deterministic error payload.
- `/api/v1/analyze` is hidden from OpenAPI/Swagger.
- Enforcement tests ensure the above cannot regress.
- Canonical supported flow is `/pipeline/shadow/run`.

## Why
- Prevents unsupported entrypoints from being used by UI or developers.
- Keeps execution model deterministic, explainable, and pipeline-scoped.

## Verification
- CI runs tests for 501 contract and OpenAPI exclusion.
