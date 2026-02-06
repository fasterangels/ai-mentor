# Phase H1: Reason Time-Decay Modeling

## Measurement only; no behavior change
- This phase is **measurement- and reporting-only**. It does **not** apply decay to analyzer decisions, confidence, or policy. No production behavior changes. Decay application is planned for H2.

## Chosen model form
- **Piecewise-linear penalty** by age band (same bands as G4: 0-30m, 30m-2h, 2h-6h, 6h-24h, 1d-3d, 3d-7d, 7d+).
- One penalty value per band in [0, 1], **monotonic non-increasing** with age (youngest band can have the highest penalty; older bands same or lower).
- Model type: `PIECEWISE_V1`. Fitting is deterministic (no optimization libraries, no randomness).

## Interpretation of penalties
- **Penalty** here is a quality factor derived from observed accuracy drop vs the youngest band:
  - Baseline = accuracy at the youngest band with sufficient support.
  - For each band: observed_drop = max(0, baseline_accuracy - band_accuracy); penalty = clamp(1 - observed_drop, 0, 1).
- Higher penalty = band performs closer to baseline (less decay). Lower penalty = band shows more accuracy drop (more decay). Penalties are then enforced to be non-increasing with age so that older evidence is never assigned a higher quality than younger.

## Minimum support rule
- Bands with **total < MIN_SUPPORT (5)** are not used for fitting. Their penalty is set by **carry-forward** from the previous (younger) band, or 1.0 for the first band. This avoids fitting on tiny counts and keeps outputs stable. (market, reason_code) groups with no band meeting MIN_SUPPORT are still emitted (all penalties 1.0) and reported as skipped_low_support in ops events.

## How to run (Part B)
- **CLI:** `python tools/live_snapshot.py --mode decay-fit`
- **Input:** G4 staleness metrics from `reports/staleness_eval/staleness_metrics_by_reason.json`. Run staleness-eval first if needed.
- **Outputs (under reports/decay_fit/):**
  - `reason_decay_params.json` — all params (fitted_at_utc, params list).
  - `reason_decay_params_by_market/*.json` — one file per market (optional).
  - `reason_decay_summary.csv` — summary for human review (optional).
- Decay-fit does **not** run in the default pipeline and does not invoke the analyzer or evaluator.
