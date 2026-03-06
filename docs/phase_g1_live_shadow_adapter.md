# Phase G1: Live Shadow Read Adapter

## What it does

- **Live read adapter (shadow-only):** Fetches raw fixture data from a live source (or a fake source in tests) and writes **snapshots** into the existing offline store (`raw_payloads` with `source_name=live_shadow`). No analysis, no decisions, no policy.
- **Provenance:** Each snapshot includes metadata: `observed_at`, `source_name`, `source_class=LIVE_SHADOW`, `checksum`, `latency_ms`, `fetch_started_at`, `fetch_ended_at`.
- **Dedup:** Snapshots are deduplicated by payload checksum (SHA-256 of canonical JSON). Re-ingesting the same payload does not create a duplicate row.

## What it explicitly does NOT do

- Does **not** run the analyzer or evaluator.
- Does **not** produce analysis runs, predictions, or policy changes.
- Does **not** affect the default pipeline or recorded-first flows.

## How to enable

- **Environment (required):**
  - `LIVE_IO_ALLOWED=true` — required to allow live read.
  - `SNAPSHOT_WRITES_ALLOWED=true` — required to write snapshots.
- **Default:** Both are **OFF**. Running without explicit opt-in returns an error payload (no exception by default so unrelated runs are not crashed).
- **Entry point:** Use `--mode live-shadow` (or the live-shadow runner) only when you intend to run live read → snapshot. Do not blend into the default orchestrator path.

## Safety constraints and failure modes

- **Blocked by flags:** If `LIVE_IO_ALLOWED` or `SNAPSHOT_WRITES_ALLOWED` is false, the adapter returns immediately with `error` and `detail` and emits `live_shadow_blocked_by_flag` ops event. It does not raise unless you call `run_live_shadow_read_blocked_or_raise()` (e.g. from CLI when user explicitly requested live-shadow).
- **Fail-fast when misused:** When the user explicitly requests live-shadow mode (e.g. CLI `--mode live-shadow`) and flags are off, the CLI can call `run_live_shadow_read_blocked_or_raise()` to raise `LiveIODisabledError` with a clear message.
- **No network in default/fake client:** The repo provides `NullLiveClient` and `FakeLiveClient`. Real network is only used if a concrete live client is configured; CI uses fake client only.
