"""Unit tests for G2 snapshot envelope: checksums, legacy defaulting, latency."""
from __future__ import annotations

import json

import pytest

from pipeline.snapshot_envelope import (
    ENVELOPE_SCHEMA_VERSION,
    compute_envelope_checksum,
    compute_latency_ms,
    compute_payload_checksum,
    parse_payload_json,
    build_envelope_for_recorded,
    build_envelope_for_live_shadow,
)
from datetime import datetime, timezone


def test_payload_checksum_deterministic():
    payload = {"a": 1, "b": 2}
    c1 = compute_payload_checksum(payload)
    c2 = compute_payload_checksum(payload)
    assert c1 == c2
    # key order should not matter
    payload2 = {"b": 2, "a": 1}
    c3 = compute_payload_checksum(payload2)
    assert c1 == c3


def test_envelope_checksum_deterministic():
    meta = {"snapshot_type": "recorded", "payload_checksum": "abc", "schema_version": 1}
    c1 = compute_envelope_checksum(meta)
    c2 = compute_envelope_checksum(meta)
    assert c1 == c2
    meta["envelope_checksum"] = "ignored"
    c3 = compute_envelope_checksum(meta)
    assert c1 == c3


def test_legacy_snapshot_read_defaults_no_crash():
    # Legacy: raw payload without metadata/payload wrapper
    legacy = {"source_name": "old", "data": {"x": 1}}
    payload_json = json.dumps(legacy)
    missing_calls = []

    def on_missing(missing_keys):
        missing_calls.append(missing_keys)

    meta, payload = parse_payload_json(
        payload_json,
        on_missing_fields=on_missing,
    )
    assert meta["snapshot_type"] == "recorded"
    assert meta["source"]["class"] == "RECORDED"
    assert meta["observed_at_utc"]
    assert meta["schema_version"] == 0
    assert payload == legacy
    assert ["legacy_no_envelope"] in missing_calls or any("legacy" in str(k) for k in missing_calls)


def test_latency_ms_computed_from_timestamps():
    start = "2025-01-01T12:00:00+00:00"
    end = "2025-01-01T12:00:01+00:00"
    lat = compute_latency_ms(start, end)
    assert lat is not None
    assert 900 <= lat <= 1100  # ~1000 ms
    assert compute_latency_ms(None, end) is None
    assert compute_latency_ms(start, None) is None


def test_build_recorded_has_required_fields():
    payload = {"match_id": "m1", "data": {}}
    now = datetime.now(timezone.utc)
    env = build_envelope_for_recorded(payload, "sid1", now, "recorded")
    d = env.to_dict()
    assert d["snapshot_type"] == "recorded"
    assert d["snapshot_id"] == "sid1"
    assert d["created_at_utc"]
    assert d["payload_checksum"] == compute_payload_checksum(payload)
    assert d["source"]["class"] == "RECORDED"
    assert d["observed_at_utc"]
    assert d["schema_version"] == ENVELOPE_SCHEMA_VERSION
    assert d["envelope_checksum"]


def test_build_live_shadow_has_timing_tags():
    payload = {"fixture_id": "f1"}
    now = datetime.now(timezone.utc)
    env = build_envelope_for_live_shadow(
        payload, "sid2", now, "live_shadow", now,
        fetch_started_at_utc=now,
        fetch_ended_at_utc=now,
        latency_ms=50.5,
    )
    d = env.to_dict()
    assert d["snapshot_type"] == "live_shadow"
    assert d["latency_ms"] == 50.5
    assert d["fetch_started_at_utc"]
    assert d["fetch_ended_at_utc"]
    assert d["envelope_checksum"]
