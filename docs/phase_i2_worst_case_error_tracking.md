# Phase I2: Worst-Case Error Tracking

## Purpose

Worst-case error tracking is **measurement-only**. It ranks evaluated decisions by loss severity so teams can focus on the biggest errors: highest-confidence wrong predictions and cases where timing/uncertainty signals would have suggested refusing.

- **No enforcement.** This phase does not change analyzer behavior, confidence, or policy. It only produces reports.
- **Offline-first.** It uses only stored snapshots, evaluation outcomes, and (optional) delta/staleness/uncertainty shadow data.
- **Deterministic.** Same inputs produce the same worst-case list and stable filenames.

## What It Ranks

The report orders decisions by a **worst-case score** so that:

1. **Incorrect predictions** (outcome = FAILURE) are ranked above correct ones.
2. **Higher original confidence** on incorrect predictions increases the score (high-confidence wrong is worse).
3. **Optional uncertainty penalty:** when uncertainty shadow data indicates the system *should have refused* but didn’t (`would_refuse == TRUE`), an extra penalty is applied.

## Fixed Scoring Definition

The score is **fixed and explainable** (weights are not tuned dynamically):

- **base** = 1 if incorrect (outcome = FAILURE), else 0  
- **weight_confidence** = original confidence (clamped to 0..1)  
- **optional_penalty** = +0.25 if uncertainty_shadow would_refuse == TRUE  

**WorstCaseScore** = base × (1 + weight_confidence + optional_penalty)

Examples:

- Correct prediction → score = 0  
- Incorrect, confidence 0.5 → score = 1 × (1 + 0.5) = 1.5  
- Incorrect, confidence 0.8, would_refuse → score = 1 × (1 + 0.8 + 0.25) = 2.05  

## Output

- **Overall and per-market:** a ranked list (top N, default 50) with stable ordering (score descending, then `fixture_id` for ties).
- **Per row:** fixture_id, market, prediction, outcome, original_confidence, worst_case_score, triggered_uncertainty_signals (if available), snapshot_ids, and **snapshot_type** (e.g. `recorded` or `live_shadow` for LIVE_SHADOW-derived snapshots).
- **Artifacts:** `worst_case_errors_top.csv` and `worst_case_errors_top.json` under the reports directory.

## How to Run

- **Backend entry:** `python backend_entry.py --ops worst-case-tracking` (from backend dir).  
- **Tools script:** `python tools/operational_run.py --mode worst-case-tracking [--output-dir reports]` (from repo root).  

Worst-case tracking **does not run by default**; it runs only when explicitly requested via one of the above.

## No Enforcement

This phase does **not**:

- Change any analyzer decisions or confidence.
- Block or allow any production writes.
- Modify policy or activation logic.

It only computes and writes reports for inspection and prioritization.
