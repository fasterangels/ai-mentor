"""
Safe live IO wrapper: recorded-first enforcement, read-only default.
Connectors are only exposed when they are RecordedPlatformAdapter or when live IO is explicitly allowed.
Live IO is allowed ONLY in shadow mode with a recorded baseline (enforced here).
Deterministic metrics for requests, failures, retries, timeouts, circuit_open, rate_limited, and latency.
"""

from __future__ import annotations

import os
import threading
import time
from contextlib import contextmanager
from contextvars import ContextVar
from pathlib import Path
from typing import Any, Dict, List, Optional

from ingestion.connectors.platform_base import DataConnector, RecordedPlatformAdapter
from ingestion.registry import get_connector

# Execution mode: "shadow" = allowed to use live IO (with baseline); anything else = not allowed when LIVE_IO_ALLOWED.
_EXECUTION_MODE: ContextVar[Optional[str]] = ContextVar("live_io_execution_mode", default=None)

LIVE_IO_SHADOW_ONLY_MESSAGE = "Live IO is allowed only in shadow mode with a recorded baseline."
RECORDED_BASELINE_REQUIRED_MESSAGE = "Recorded baseline required for live IO: connector {name!r} has no fixtures or empty fixtures directory."

# Module-level metrics (thread-safe for single-threaded runner; use lock for safety)
_metrics_lock = threading.Lock()
_counters: Dict[str, int] = {
    "requests_total": 0,
    "failures_total": 0,
    "retries_total": 0,
    "timeouts_total": 0,
    "circuit_open_total": 0,
    "rate_limited_total": 0,
}
_latency_ms: List[float] = []


def get_execution_mode() -> str:
    """Current execution mode. \"shadow\" = live IO allowed (with baseline); else live IO not allowed when LIVE_IO_ALLOWED."""
    return (_EXECUTION_MODE.get() or "").strip()


@contextmanager
def execution_mode_context(mode: str):
    """Context manager to run code in a given execution mode (e.g. \"shadow\")."""
    token = _EXECUTION_MODE.set(mode)
    try:
        yield
    finally:
        _EXECUTION_MODE.reset(token)


def set_execution_mode(mode: str) -> Any:
    """Set execution mode; returns a token to pass to reset_execution_mode."""
    return _EXECUTION_MODE.set(mode)


def reset_execution_mode(token: Any) -> None:
    """Restore execution mode after set_execution_mode."""
    _EXECUTION_MODE.reset(token)


def _fixtures_dir_for_connector(connector_name: str) -> Path:
    """Resolve backend/ingestion/fixtures/<connector_name>."""
    base = Path(__file__).resolve().parent.parent
    return base / "ingestion" / "fixtures" / connector_name


def assert_recorded_baseline_exists(connector_name: str) -> None:
    """
    Fail fast if recorded baseline (fixtures dir with at least one JSON) does not exist for connector.
    Raises ValueError with deterministic message when missing.
    """
    fixtures_dir = _fixtures_dir_for_connector(connector_name)
    if not fixtures_dir.is_dir():
        raise ValueError(RECORDED_BASELINE_REQUIRED_MESSAGE.format(name=connector_name))
    json_files = list(fixtures_dir.glob("*.json"))
    if not json_files:
        raise ValueError(RECORDED_BASELINE_REQUIRED_MESSAGE.format(name=connector_name))


def live_io_allowed() -> bool:
    """True if live (non-recorded) connectors are allowed. Default: False (recorded-first)."""
    return os.environ.get("LIVE_IO_ALLOWED", "").strip().lower() in ("1", "true", "yes")


def live_writes_allowed() -> bool:
    """True if live writes (e.g. persist, cache) are allowed. Default: False (read-only default)."""
    return os.environ.get("LIVE_WRITES_ALLOWED", "").strip().lower() in ("1", "true", "yes")


def get_connector_safe(name: str) -> Optional[DataConnector]:
    """
    Return the connector only if it is safe to use under current policy:
    - RecordedPlatformAdapter: always allowed (recorded-first).
    - Other connectors: only when LIVE_IO_ALLOWED is true AND execution_mode is "shadow" AND recorded baseline exists.
    Raises ValueError if LIVE_IO_ALLOWED but not in shadow mode, or if baseline missing.
    Returns None if not found or not allowed (e.g. LIVE_IO_ALLOWED false).
    """
    adapter = get_connector(name)
    if adapter is None:
        return None
    if isinstance(adapter, RecordedPlatformAdapter):
        return adapter
    if not live_io_allowed():
        return None
    # Live IO allowed: enforce shadow-only and recorded baseline
    if get_execution_mode() != "shadow":
        raise ValueError(LIVE_IO_SHADOW_ONLY_MESSAGE)
    assert_recorded_baseline_exists(name)
    return adapter


def record_request(
    *,
    success: bool,
    latency_ms: float,
    retries: int = 0,
    timeout: bool = False,
    circuit_open: bool = False,
    rate_limited: bool = False,
) -> None:
    """
    Record one live IO request for metrics. Deterministic: only uses provided values.
    Call from code that performs live IO (e.g. after fetch_match_data for live connectors).
    """
    with _metrics_lock:
        _counters["requests_total"] = _counters.get("requests_total", 0) + 1
        if not success:
            _counters["failures_total"] = _counters.get("failures_total", 0) + 1
        if retries > 0:
            _counters["retries_total"] = _counters.get("retries_total", 0) + retries
        if timeout:
            _counters["timeouts_total"] = _counters.get("timeouts_total", 0) + 1
        if circuit_open:
            _counters["circuit_open_total"] = _counters.get("circuit_open_total", 0) + 1
        if rate_limited:
            _counters["rate_limited_total"] = _counters.get("rate_limited_total", 0) + 1
        _latency_ms.append(round(latency_ms, 2))


def _percentile(sorted_values: List[float], p: float) -> float:
    """Compute percentile (0..100). Returns 0.0 if empty."""
    if not sorted_values:
        return 0.0
    k = (len(sorted_values) - 1) * (p / 100.0)
    f = int(k)
    c = f + 1 if f + 1 < len(sorted_values) else f
    return float(sorted_values[f] + (k - f) * (sorted_values[c] - sorted_values[f]))


def live_io_metrics_snapshot() -> Dict[str, Any]:
    """
    Return a deterministic snapshot of current live IO metrics.
    Counters and latency stats (p50, p95) from measured durations only; no wall-clock dependency.
    """
    with _metrics_lock:
        counters = dict(_counters)
        latencies = list(_latency_ms)
    sorted_lat = sorted(latencies) if latencies else []
    return {
        "counters": dict(counters),
        "latency_ms": {
            "count": len(sorted_lat),
            "p50": round(_percentile(sorted_lat, 50), 2),
            "p95": round(_percentile(sorted_lat, 95), 2),
        },
    }


def reset_metrics() -> None:
    """Reset all metrics (for tests)."""
    with _metrics_lock:
        for k in _counters:
            _counters[k] = 0
        _latency_ms.clear()
