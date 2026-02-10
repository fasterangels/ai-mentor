# Phase H2: Confidence Penalty Shadow Reporting

## No effect on decisions yet
- This phase is **shadow-only**. Confidence penalties are **computed and reported only**. There is **no effect on analyzer outputs, decisions, or policy**. Production behavior is unchanged.

## What it does
- For each evaluated decision (from existing analysis runs + resolutions + predictions):
  - Uses evidence age (G4 proxy) to get an age band per run.
  - Looks up decay params (from H1) per (market, reason_code).
  - Computes a **hypothetical** penalized confidence (original_confidence × penalty_factor) and stores it in reports only.
- Writes:
  - `reports/confidence_penalty_shadow/confidence_penalty_shadow.csv`
  - `reports/confidence_penalty_shadow/confidence_penalty_shadow.json`
- Outputs are deterministic with stable row ordering (run_id, market, reason_code).

## How to run
- **CLI:** `python tools/live_snapshot.py --mode confidence-penalty-shadow`
- Requires DB with evaluation data and (optionally) `reports/decay_fit/reason_decay_params.json`. If decay params are missing, penalty_factor is 1.0 (no penalty).
- Does **not** run in the default pipeline.
