# Project Status (Deterministic / Offline-first)

## Canonical Flow
- Supported: `/pipeline/shadow/run`

## Disabled Endpoints
- `/api/v1/analyze` — intentionally not supported (501), hidden from OpenAPI/Swagger

## Safety Gates
- Live IO default OFF; recorded-first enforced
- Shadow tuner proposes only; production behavior unchanged
- Guardrails and caps enforced; ops events emitted

## Injury news shadow attach
- Optional report section `injury_news_shadow_summary` in pipeline report when `INJ_NEWS_SHADOW_ATTACH_ENABLED=1` (default off).
- Guarantee: no decision changes; shadow-only. Decisions and confidences are identical with the flag on or off.
- Used for observability and future policy; not used for picks.

## Verification
- CI tests enforce `/api/v1/analyze` 501 contract and OpenAPI exclusion
- CI verifies pipeline/evaluation/tuner regression gates
