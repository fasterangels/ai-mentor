# Phase H1: Reason Decay Model (Foundation)

## Measurement only
- This phase is **measurement-only**. It does not apply decay to analyzer decisions, confidence, or policy. No production behavior changes.
- Input: G4 staleness metrics (aggregated by market, reason_code, age_band: total, correct, accuracy).
- Output: Fitted decay model parameters and reports stored as JSON artifacts. Not activated in the pipeline.

## Model form: piecewise-linear penalty (Option 1)
- **Model type:** `PIECEWISE_V1`
- **Bands:** Same as G4: 0-30m, 30m-2h, 2h-6h, 6h-24h, 1d-3d, 3d-7d, 7d+.
- **Parameters:** One penalty per band in [0, 1], **monotonic non-increasing** with age (youngest band can have highest penalty value; older bands same or lower).
- **Fitting:** Deterministic, no optimization libraries or randomness.
  - Baseline accuracy = accuracy at youngest band with sufficient support.
  - Observed drop = max(0, baseline_accuracy - band_accuracy).
  - Penalty = clamp(1 - observed_drop, 0, 1).
  - Bands with total < MIN_SUPPORT (5): penalty carried forward from previous band (or 1.0).
  - Monotonicity enforced: penalty[i] >= penalty[i+1] (young to old).

## No decay/dampening implemented
- Fitted parameters are stored for reporting and future use. **No time-decay or dampening is applied** to the analyzer in this phase.

## Artifacts
- **DecayModelParams** per (market, reason_code): schema_version, model_type, bands, penalty_by_band, fitted_at_utc, fit_quality.
- **Fit diagnostics:** bands_with_support, coverage_counts, optional mse_vs_baseline.
- JSON under reports dir (stable keys, sort_keys=True). Optional versioned policy JSON in shadow-only area is not activated.

## Modules
- `backend/modeling/reason_decay/model.py` — data structures, serialization.
- `backend/modeling/reason_decay/fit_piecewise.py` — deterministic fitting (MIN_SUPPORT, monotonicity, clamp).
