"""Unit tests for live IO metrics aggregation and snapshot."""

from __future__ import annotations

import sys
from pathlib import Path

_backend = Path(__file__).resolve().parent.parent.parent
if str(_backend) not in sys.path:
    sys.path.insert(0, str(_backend))

import pytest

from ingestion.live_io import (
    live_io_metrics_snapshot,
    record_request,
    reset_metrics,
)


def test_metrics_snapshot_empty() -> None:
    """Empty snapshot has zero counters and zero latency stats."""
    reset_metrics()
    snap = live_io_metrics_snapshot()
    assert snap["counters"]["requests_total"] == 0
    assert snap["counters"]["failures_total"] == 0
    assert snap["latency_ms"]["count"] == 0
    assert snap["latency_ms"]["p50"] == 0.0
    assert snap["latency_ms"]["p95"] == 0.0


def test_record_request_increments_counters() -> None:
    """record_request updates counters and latency list."""
    reset_metrics()
    record_request(success=True, latency_ms=10.5)
    record_request(success=False, latency_ms=20.0)
    record_request(success=True, latency_ms=30.0, retries=2)
    record_request(success=False, latency_ms=5.0, timeout=True)
    snap = live_io_metrics_snapshot()
    assert snap["counters"]["requests_total"] == 4
    assert snap["counters"]["failures_total"] == 2
    assert snap["counters"]["retries_total"] == 2
    assert snap["counters"]["timeouts_total"] == 1
    assert snap["latency_ms"]["count"] == 4
    assert 5 <= snap["latency_ms"]["p50"] <= 30
    assert snap["latency_ms"]["p95"] <= 31


def test_metrics_snapshot_deterministic() -> None:
    """Same recorded values yield same snapshot (deterministic)."""
    reset_metrics()
    for _ in range(5):
        record_request(success=True, latency_ms=100.0)
    snap1 = live_io_metrics_snapshot()
    snap2 = live_io_metrics_snapshot()
    assert snap1["counters"] == snap2["counters"]
    assert snap1["latency_ms"]["p50"] == snap2["latency_ms"]["p50"]
    assert snap1["latency_ms"]["p95"] == snap2["latency_ms"]["p95"]


def test_reset_metrics_clears_state() -> None:
    """reset_metrics clears counters and latency list."""
    reset_metrics()
    record_request(success=True, latency_ms=1.0)
    reset_metrics()
    snap = live_io_metrics_snapshot()
    assert snap["counters"]["requests_total"] == 0
    assert snap["latency_ms"]["count"] == 0
