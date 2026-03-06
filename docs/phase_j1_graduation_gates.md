# Phase J1: Graduation Gates

## Overview

Graduation gates are **measurement-only** pass/fail criteria over existing reports (G3, G4, H1, H2, H3, I1, I2, I3). They do **not** change production behavior, analyzer output, or live activation.

## What is enforced

**Nothing is automatically enforced.** The evaluator computes PASS/FAIL per criterion and overall for **review only**. All eight v1 criteria must PASS for overall graduation; no partial pass.

- **DELTA_COVERAGE**: At least N fixtures with both recorded and live_shadow deltas (default N=50).
- **DELTA_PAYLOAD_MATCH_RATE**: payload_match rate ≥ 0.95 (from G3).
- **STALENESS_OBSERVABILITY**: G4 report exists with ≥ M reason_codes with non-zero support (default M=20).
- **DECAY_MODEL_COVERAGE**: H1 decay params for ≥ M reason_codes with fit diagnostics (default M=20).
- **UNCERTAINTY_SIGNAL_AVAILABILITY**: H3 uncertainty_shadow covers ≥ N decisions (default N=200).
- **LATE_DATA_ROBUSTNESS**: I1 late-data replay; accuracy_delta_24h ≥ -0.10 or refusal_delta_24h ≥ +0.05.
- **WORST_CASE_VISIBILITY**: I2 worst-case report exists with ≥ K rows (default K=20).
- **REFUSAL_OPT_REPORTING**: I3 artifacts exist (best overall + grid summary).

## Strict nature

- **Deterministic**: Same inputs → same pass/fail outcome.
- **Strict pass/fail only**: No “maybe” and no auto-tuning of thresholds.
- **Offline-first**: Uses only existing reports/artifacts; no live activation.

## No automation

Graduation evaluation does **not** run by default. It is invoked explicitly:

- **CLI:** `python tools/operational_run.py --mode graduation-eval [--output-dir reports]` (from repo root).
- **Backend entry:** `python backend_entry.py --ops graduation-eval` (from backend dir; uses `REPORTS_DIR` env, default `reports`).

## Output artifacts

Written under the reports directory:

1. **graduation_result.json** — Machine-readable: overall_pass, criteria (name, pass, details), computed_at_utc, thresholds_used.
2. **graduation_result.md** — Human-readable: overall PASS/FAIL, each criterion with short details, and the exact thresholds used.
