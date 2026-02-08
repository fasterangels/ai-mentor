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

## Project Status — Completed (Deterministic / Offline-first)

- **Canonical supported flow:** `/pipeline/shadow/run`
- **Unsupported endpoints:**
  - `/api/v1/analyze` → 501, excluded from OpenAPI
- **Safety defaults:**
  - Live IO disabled
  - Snapshot writes disabled
  - Replay disabled
  - Shadow learning only
- **Guarantees:**
  - Deterministic outputs
  - Explainable reasons with evidence
  - Offline evaluation with ground truth
  - Shadow-only evolution under constraints
- **Note:** Any future capability must be added as shadow-first and audited.
