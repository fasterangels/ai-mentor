"""Unit tests for live IO guardrail evaluation."""

from __future__ import annotations

import sys
from pathlib import Path

_backend = Path(__file__).resolve().parent.parent.parent
if str(_backend) not in sys.path:
    sys.path.insert(0, str(_backend))

import pytest

from guardrails.live_io_guardrails import DEFAULT_POLICY, evaluate


def test_evaluate_disabled_without_live_io_allowed() -> None:
    """When LIVE_IO_ALLOWED is false, evaluate returns no alerts (guardrails disabled)."""
    with pytest.MonkeyPatch.context() as m:
        m.setenv("LIVE_IO_ALLOWED", "0")
        metrics = {
            "counters": {"requests_total": 100, "failures_total": 50},
            "latency_ms": {"count": 100, "p50": 10, "p95": 10000},
        }
        alerts = evaluate(metrics, policy=None)
        assert alerts == []


def test_evaluate_enabled_with_high_failure_rate() -> None:
    """When LIVE_IO_ALLOWED=true and failure rate exceeds threshold, WARN alert."""
    with pytest.MonkeyPatch.context() as m:
        m.setenv("LIVE_IO_ALLOWED", "1")
        metrics = {
            "counters": {"requests_total": 10, "failures_total": 5},
            "latency_ms": {"count": 10, "p50": 10, "p95": 50},
        }
        alerts = evaluate(metrics, policy=None)
        codes = [a["code"] for a in alerts]
        assert "LIVE_IO_HIGH_FAILURE_RATE" in codes


def test_evaluate_enabled_with_high_p95() -> None:
    """When p95 exceeds max_p95_latency_ms, WARN alert."""
    with pytest.MonkeyPatch.context() as m:
        m.setenv("LIVE_IO_ALLOWED", "1")
        metrics = {
            "counters": {"requests_total": 5, "failures_total": 0},
            "latency_ms": {"count": 5, "p50": 100, "p95": 6000},
        }
        alerts = evaluate(metrics, policy=None)
        codes = [a["code"] for a in alerts]
        assert "LIVE_IO_HIGH_P95_LATENCY" in codes


def test_evaluate_enabled_normal_metrics_no_alerts() -> None:
    """When metrics are within policy, no alerts."""
    with pytest.MonkeyPatch.context() as m:
        m.setenv("LIVE_IO_ALLOWED", "1")
        metrics = {
            "counters": {"requests_total": 10, "failures_total": 0, "timeouts_total": 0, "rate_limited_total": 0},
            "latency_ms": {"count": 10, "p50": 50, "p95": 200},
        }
        alerts = evaluate(metrics, policy=None)
        assert len(alerts) == 0


def test_evaluate_explicit_policy_disabled() -> None:
    """Policy enabled=False returns no alerts even with bad metrics."""
    metrics = {
        "counters": {"requests_total": 10, "failures_total": 9},
        "latency_ms": {"count": 10, "p50": 10, "p95": 10000},
    }
    alerts = evaluate(metrics, policy={"enabled": False})
    assert alerts == []
