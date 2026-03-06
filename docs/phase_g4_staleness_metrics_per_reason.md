# Phase G4: Staleness Metrics per Reason

**Measurement only.** No changes to analyzer decisions, confidence, or policy. Offline-first; deterministic outputs.

## What is measured
- Per (market, reason_code, age_band): count_total, count_correct, accuracy, neutral_rate, avg_confidence.
- Evidence age is assigned to fixed bands: 0–30m, 30m–2h, 2h–6h, 6h–24h, 1d–3d, 3d–7d, 7d+.
- Measurement only; no good/bad judgment.

## Limitations of proxy mapping
- Evidence timestamp is a **provisional proxy**: `reason_code_age_ms := decision_time_utc - snapshot.observed_at_utc` (or effective_from_utc if present). The snapshot is the pipeline_cache payload for the same match_id with observed_at ≤ decision time (latest such). Per-reason evidence (e.g. injuries/news) is not wired yet; all reasons for a decision share the same snapshot-level age until evidence-to-reason linkage is added later.

## No decay/dampening yet
- This phase does **not** implement time-decay, dampening, or any policy changes. It only measures observed performance by age band. Phase H will use these metrics for decay modeling.

## How to run
- `python tools/live_snapshot.py --mode staleness-eval`
- Reports are written under `reports/staleness_eval/`: `staleness_metrics_by_reason.csv`, `staleness_metrics_by_reason.json`, plus timestamped run files.
