# Changelog

## [1.0.0]

### Features

- **Analyzer & analysis API** — /api/v1/analyze is intentionally not supported (501). Use /pipeline/shadow/run. Analysis runs inside the pipeline (resolver + analyzer outcomes).
- **Shadow modes** — Live shadow compare and live shadow analyze (read-only unless LIVE_WRITES_ALLOWED).
- **Activation gates** — Kill-switch, burn-in mode, optional activation with guardrails.
- **Burn-in ops** — Single pipeline: ingestion → compare → analyze → optional activation; report bundles under reports/burn_in/.
- **Health check** — CLI and readiness checks for DB, connector, policy.
- **Quality audit** — Reason effectiveness, calibration, stability; suggestions for shadow tuning.
- **Tuning planner** — Guided policy tuning from quality_audit; replay regression; ops plan-tuning CLI.
- **Reports viewer API** — Read-only GET /api/v1/reports/index, /item/{run_id}, /file?path=; optional X-Reports-Token.
- **Version** — VERSION file; GET /api/v1/meta/version and CLI --version.

### Docs

- Release checklist (docs/release_checklist_v1.md) and system overview (docs/system_overview_v1.md).
- Burn-in runbook (docs/runbook_burnin.md).
