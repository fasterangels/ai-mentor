# Phase G2: Snapshot Provenance & Timing Tags

## Purpose

Every snapshot (recorded and live_shadow) carries standardized **provenance** and **timing** metadata so later phases (G3/G4/H*) can measure latency and staleness without ambiguity. **No staleness logic is implemented in G2** — this phase only adds and stores the tags.

## Standard Fields (SnapshotEnvelope v1)

### Required

- **snapshot_id** — Identifier (e.g. payload hash or cache key).
- **snapshot_type** — `"recorded"` | `"live_shadow"` | etc.
- **created_at_utc** — When the snapshot record was created (ISO UTC).
- **payload_checksum** — SHA-256 of canonical JSON of the payload (hex).
- **source** — Object:
  - **class** — `RECORDED` | `LIVE_SHADOW` | `EDITORIAL` | `UNKNOWN`
  - **name** — String (e.g. `"pipeline_cache"`, `"live_shadow"`)
  - **ref** — Optional string (e.g. URL/id).
  - **reliability_tier** — `HIGH` | `MED` | `LOW`
- **observed_at_utc** — When the source data was observed (ISO UTC). For recorded, may equal `created_at_utc` if not known.
- **schema_version** — Integer (1 for G2).

### Timing (all UTC, optional)

- **fetch_started_at_utc** — When fetch began.
- **fetch_ended_at_utc** — When fetch ended.
- **latency_ms** — Computed from fetch timestamps when both exist.
- **effective_from_utc** / **expected_valid_until_utc** — Reserved for future use.

### Integrity / audit

- **envelope_checksum** — SHA-256 of canonicalized envelope metadata **excluding** `envelope_checksum` itself. Used to detect tampering; mismatch is logged via `snapshot_integrity_check_failed` and does not fail the pipeline by default.

## Storage Format

- **DB (RawPayload.payload_json):** JSON string with top-level keys:
  - **metadata** — The envelope (all fields above).
  - **payload** — The raw payload (unchanged for analysis).
- **Legacy:** Snapshots written before G2 may have no envelope (plain payload JSON). When reading, missing fields are defaulted and `snapshot_envelope_missing_fields` is emitted.

## Defaulting Rules for Legacy Snapshots

When `metadata`/`payload` are missing or fields are absent:

- **observed_at_utc** := `created_at_utc` or row creation time.
- **schema_version** := 0 (legacy).
- **source** := `{ "class": "RECORDED", "name": "recorded", "ref": null, "reliability_tier": "HIGH" }`.
- **snapshot_id** := `payload_checksum` if present, else empty string.
- The pipeline **never crashes** on missing new fields.

## Checksum Approach

- **Payload:** `compute_payload_checksum(payload)` = SHA-256 of `canonical_json(payload)` (sorted keys, no extra whitespace).
- **Envelope:** `compute_envelope_checksum(metadata)` = SHA-256 of canonical JSON of metadata with `envelope_checksum` key removed. Stored in `metadata.envelope_checksum` for new writes.

## Ops Events

- **snapshot_write_start** / **snapshot_write_end** — When writing a snapshot (with duration).
- **snapshot_envelope_missing_fields** — When reading legacy snapshots and defaulting fields.
- **snapshot_integrity_check_failed** — When stored `envelope_checksum` does not match recomputed value (logged only; pipeline continues).

## What G2 Does Not Do

- **No staleness logic** — No decisions based on age or validity windows.
- **No change to analysis/decisions** — Provenance and timing are metadata only.
- **No network** — Offline-first preserved; live remains shadow-only.
