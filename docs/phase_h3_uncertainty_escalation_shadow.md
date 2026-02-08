# Phase H3: Uncertainty Escalation Shadow (Simulation Only)

## Simulation only; no refusals enforced
- This phase is **shadow-only**. It **simulates** “would-refuse” outcomes from uncertainty signals and writes reports. **No refusals are enforced** in production; analyzer outputs and behavior are unchanged.

## Refusal simulation rule (fixed)
- **would_refuse = TRUE** if:
  - **(STALE_EVIDENCE AND LOW_EFFECTIVE_CONFIDENCE)** OR
  - **(>= 2 uncertainty signals triggered)**
- Thresholds are not tuned dynamically.

## What it does
- For each evaluated decision: loads decision record, confidence penalty shadow rows, and decay params; computes uncertainty profile (Part A) and then **would_refuse** using the rule above.
- Writes:
  - `reports/uncertainty_shadow/uncertainty_shadow.csv`
  - `reports/uncertainty_shadow/uncertainty_shadow.json`
- Outputs are deterministic with stable row ordering (run_id).

## How to run
- **CLI:** `python tools/live_snapshot.py --mode uncertainty-shadow`
- Requires DB with evaluation data, and (optionally) `reports/confidence_penalty_shadow/confidence_penalty_shadow.json` and `reports/decay_fit/reason_decay_params.json`. If inputs are missing, signals may not trigger.
- Does **not** run in the default pipeline.
