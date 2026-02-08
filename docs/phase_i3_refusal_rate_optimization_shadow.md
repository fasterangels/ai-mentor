# Phase I3: Refusal Rate Optimization (Shadow-Only)

## Purpose

Refusal optimization finds threshold settings that would improve **safety under pressure** on historical data, using a fixed objective and grid search. It is **shadow-only**: no refusals are enforced in production and analyzer outputs are unchanged.

- **Offline-first:** Uses only uncertainty-shadow outputs (e.g. H3) and evaluation outcomes.
- **Deterministic:** Same inputs produce the same optimal thresholds and artifact ordering.
- **No black-box ML:** Grid search over fixed threshold ranges only.

## What It Optimizes

- **Refuse rule (simulation):** Refuse = TRUE when `(age_band >= stale_band_threshold) AND (effective_confidence < effective_confidence_threshold)`.
- **Objective (maximize):** `safety_score = accuracy_on_non_refused - 0.10 * refusal_rate`. Accuracy excludes neutrals (success / (success + failure)).
- **Grid:** `effective_confidence_threshold` from 0.10 to 0.90 (step 0.05); `stale_band_threshold` in 6-24h, 1-3d, 3-7d, 7d+.

## How to Run

- **Backend entry:** `python backend_entry.py --ops refusal-optimize-shadow` (from backend dir). Writes to `REPORTS_DIR` (default `reports`).
- **Tools script:** `python tools/operational_run.py --mode refusal-optimize-shadow [--output-dir reports]` (from repo root).

The mode **does not run by default**; it runs only when explicitly requested.

## Output Artifacts

Written under the reports directory:

1. **refusal_optimization_best_overall.json** — Best thresholds and metrics overall.
2. **refusal_optimization_best_by_market.json** — Best thresholds per market (one_x_two, over_under_25, gg_ng).
3. **refusal_optimization_grid_summary.csv** — Full grid: market, stale_band_threshold, effective_confidence_threshold, refusal_rate, accuracy_on_non_refused, safety_score, support_total.
4. **refusal_optimization_notes.md** — Fixed objective, grid ranges, tie-breaker rules, and shadow-only disclaimer.

If uncertainty-shadow or evaluation input is missing, the runner emits an ops event and writes **empty** artifacts (no crash).

## Why Shadow-Only

This phase is for **review and tuning only**. It does **not**:

- Change analyzer decisions or confidence.
- Enforce refusals in production.
- Modify policy or activation logic.

Results are for inspection and future policy design, not for live enforcement.
