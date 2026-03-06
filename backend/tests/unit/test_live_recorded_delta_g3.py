"""Unit tests for G3 live vs recorded delta evaluation."""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from evaluation.live_recorded_delta import (
    DeltaReport,
    SnapshotMeta,
    STATUS_COMPLETE,
    STATUS_INCOMPLETE,
    _compute_delta,
    _observed_at_key,
)


def test_delta_incomplete_when_recorded_missing():
    live = SnapshotMeta(
        snapshot_id="l1",
        snapshot_type="live_shadow",
        observed_at_utc="2025-01-01T12:00:00+00:00",
        payload_checksum="c1",
        envelope_checksum="e1",
        latency_ms=50.0,
        source_name="live_shadow",
        row_id=1,
    )
    now = datetime.now(timezone.utc)
    r = _compute_delta("f1", None, live, now)
    assert r.status == STATUS_INCOMPLETE
    assert r.recorded_snapshot_id is None
    assert r.live_snapshot_id == "l1"


def test_delta_incomplete_when_live_missing():
    rec = SnapshotMeta(
        snapshot_id="r1",
        snapshot_type="recorded",
        observed_at_utc="2025-01-01T12:00:00+00:00",
        payload_checksum="c1",
        envelope_checksum="e1",
        latency_ms=10.0,
        source_name="pipeline_cache",
        row_id=1,
    )
    now = datetime.now(timezone.utc)
    r = _compute_delta("f1", rec, None, now)
    assert r.status == STATUS_INCOMPLETE
    assert r.recorded_snapshot_id == "r1"
    assert r.live_snapshot_id is None


def test_delta_complete_calculations():
    rec = SnapshotMeta(
        snapshot_id="r1",
        snapshot_type="recorded",
        observed_at_utc="2025-01-01T12:00:00+00:00",
        payload_checksum="c1",
        envelope_checksum="e1",
        latency_ms=10.0,
        source_name="pipeline_cache",
        row_id=1,
    )
    live = SnapshotMeta(
        snapshot_id="l1",
        snapshot_type="live_shadow",
        observed_at_utc="2025-01-01T12:00:01+00:00",
        payload_checksum="c1",
        envelope_checksum="e2",
        latency_ms=25.0,
        source_name="live_shadow",
        row_id=2,
    )
    now = datetime.now(timezone.utc)
    r = _compute_delta("f1", rec, live, now)
    assert r.status == STATUS_COMPLETE
    assert r.observed_at_delta_ms is not None
    assert 900 <= r.observed_at_delta_ms <= 1100
    assert r.fetch_latency_delta_ms == 15.0
    assert r.payload_match is True
    assert r.envelope_match is False


def test_observed_at_key_sort():
    a = "2025-01-01T12:00:00+00:00"
    b = "2025-01-01T12:00:01+00:00"
    assert _observed_at_key(a) < _observed_at_key(b)


def test_delta_report_to_dict():
    r = DeltaReport(
        fixture_id="f1",
        status=STATUS_COMPLETE,
        recorded_snapshot_id="r1",
        live_snapshot_id="l1",
        observed_at_delta_ms=100.5,
        fetch_latency_delta_ms=10.0,
        payload_match=True,
        envelope_match=False,
        computed_at_utc="2025-01-01T12:00:00Z",
    )
    d = r.to_dict()
    assert d["fixture_id"] == "f1"
    assert d["status"] == STATUS_COMPLETE
    assert d["observed_at_delta_ms"] == 100.5
    assert d["payload_match"] is True
    assert d["envelope_match"] is False
