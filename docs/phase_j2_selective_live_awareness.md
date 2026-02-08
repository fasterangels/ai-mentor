# Phase J2: Selective Live Awareness

## Overview

Live awareness is **informational only**: it summarizes whether live_shadow snapshots exist for a scope (e.g. fixture) and their freshness vs recorded. It does **not** trigger ingestion, analysis, or any decisions. No action, no behavior change.

## What it does

- Reads **existing** stored snapshots (pipeline_cache = recorded, live_shadow = live shadow).
- For a given scope (fixture_id minimum):
  - **has_live_shadow**: whether any live_shadow snapshot exists for that fixture.
  - **latest_live_observed_at_utc** / **latest_recorded_observed_at_utc**: latest observed timestamps.
  - **observed_gap_ms**: when both exist, `latest_live − latest_recorded` in milliseconds (staleness gap).
- Writes deterministic artifacts for review: `live_awareness.json` and `live_awareness.md`.

## No action, no decisions

- Live awareness **does not** run ingestion, analyzer, or evaluator.
- It **does not** change activation, confidence, or any production decision.
- It is **explicit mode only** and must not run by default.

## How to run

- **CLI (from repo root):**  
  `python tools/operational_run.py --mode live-awareness --fixture-id <id> [--output-dir reports]`
- **Backend entry (from backend dir):**  
  `python backend_entry.py --ops live-awareness`  
  (requires `FIXTURE_ID` and optionally `REPORTS_DIR` in the environment.)

## Output artifacts

Written under the reports directory:

1. **live_awareness.json** — Machine-readable: schema_version, computed_at_utc, scope_id, has_live_shadow, latest timestamps, observed_gap_ms, notes.
2. **live_awareness.md** — Short human summary: scope, has live shadow, latest timestamps, gap, notes.
