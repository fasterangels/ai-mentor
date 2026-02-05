# System overview v1

High-level architecture, modes, and ops commands for AI Mentor v1.

---

## Architecture

- **Backend:** FastAPI app (Python). Serves analyze, evaluation, pipeline, runner, reports, and meta APIs. Persists data in SQLite (configurable via `DATABASE_URL`).
- **Frontend:** React (Tauri or browser). Calls backend for analysis, history, settings.
- **Reports:** Read-only index at `reports/index.json`; report bundles under `reports/<subdir>/` (burn_in, tuning_plan, live_shadow_compare, etc.). Reports viewer API: `GET /api/v1/reports/index`, `GET /api/v1/reports/item/{run_id}`, `GET /api/v1/reports/file?path=...`.
- **Version:** Single source in repo root `VERSION` file. Exposed via `GET /api/v1/meta/version` and CLI `ai-mentor --version` (or `python tools/ops.py --version`).

---

## Modes

### Shadow compare

- **Purpose:** Diff live vs recorded ingestion (normalization only; no analyzer, no decisions).
- **API:** `POST /api/v1/reports/live-shadow/run` with `{"connector_name": "..."}`. `GET /api/v1/reports/live-shadow/latest` for latest summary.
- **Writes:** Only if `LIVE_WRITES_ALLOWED=true`; otherwise in-memory only. Reports under `reports/live_shadow_compare/<run_id>.json`.

### Shadow analyze

- **Purpose:** Full pipeline with analyzer (decisions ON); compare vs recorded. No policy activation; no DB/cache writes unless explicitly allowed.
- **API:** `POST /api/v1/reports/live-shadow-analyze/run`. `GET /api/v1/reports/live-shadow-analyze/latest` for latest summary.
- **Writes:** Hard-blocked for DB/cache unless `LIVE_WRITES_ALLOWED=true`. Reports under `reports/live_shadow_analyze/<run_id>.json`.

### Activation gates

- **Kill-switch:** `ACTIVATION_KILL_SWITCH=true` forces shadow-only (no writes, no activation).
- **Master switch:** `ACTIVATION_ENABLED=true` required for any activation (including burn-in).
- **Burn-in mode:** `ACTIVATION_MODE=burn_in` with stricter caps (e.g. 1–3 matches, higher confidence). See **docs/runbook_burnin.md**.

---

## Ops commands

- **Burn-in run:** `python tools/ops.py burn-in-run [--connector NAME] [--dry-run] [--activation]`  
  Ingestion → live shadow compare → live shadow analyze → (optional) burn-in activation. Writes bundle to `reports/burn_in/<run_id>/` and updates index.
- **Health check:** `python tools/ops.py health-check` — Validates DB, tables, connector, policy.
- **Plan tuning:** `python tools/ops.py plan-tuning [--last-n N] [--dry-run]` — Quality audit → tuning plan → replay regression; outputs PASS/FAIL.
- **Version:** `python tools/ops.py --version` — Prints version from `VERSION` file.

---

## Key config

- **REPORTS_DIR** — Override reports root (default `reports/`).
- **REPORTS_READ_TOKEN** — If set, reports viewer API requires `X-Reports-Token` header.
- **LIVE_IO_ALLOWED**, **LIVE_WRITES_ALLOWED**, **ACTIVATION_*** — See runbook and README.
