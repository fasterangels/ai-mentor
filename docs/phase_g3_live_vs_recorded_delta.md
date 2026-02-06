# Phase G3: Live vs Recorded Delta Evaluation

## What is measured
- observed_at_delta_ms, fetch_latency_delta_ms, payload_match, envelope_match. Metrics only.

## What is not inferred
- No decisions, no policy.

## How to run
- python tools/live_snapshot.py --mode delta-eval
