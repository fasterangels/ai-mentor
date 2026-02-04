"""
Safe live IO wrapper: recorded-first enforcement, read-only default.
Connectors are only exposed when they are RecordedPlatformAdapter or when live IO is explicitly allowed.
Deterministic metrics for requests, failures, retries, timeouts, circuit_open, rate_limited, and latency.
"""

from __future__ import annotations

import os
import threading
import time
from typing import Any, Dict, List, Optional

from ingestion.connectors.platform_base import DataConnector, RecordedPlatformAdapter
from ingestion.registry import get_connector

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
    - Other connectors: only when LIVE_IO_ALLOWED is true.
    Returns None if not found or not allowed.
    """
    adapter = get_connector(name)
    if adapter is None:
        return None
    if isinstance(adapter, RecordedPlatformAdapter):
        return adapter
    if live_io_allowed():
        return adapter
    return None


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
