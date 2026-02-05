# Project Status (Deterministic / Offline-first)

## Canonical Flow
- Supported: `/pipeline/shadow/run`

## Disabled Endpoints
- `/api/v1/analyze` — intentionally not supported (501), hidden from OpenAPI/Swagger

## Safety Gates
- Live IO default OFF; recorded-first enforced
- Shadow tuner proposes only; production behavior unchanged
- Guardrails and caps enforced; ops events emitted

## Verification
- CI tests enforce `/api/v1/analyze` 501 contract and OpenAPI exclusion
- CI verifies pipeline/evaluation/tuner regression gates

See [BASELINE.md](BASELINE.md) for copy-paste run commands.
