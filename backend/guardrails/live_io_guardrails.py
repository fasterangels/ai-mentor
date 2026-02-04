"""
Live IO guardrail evaluator: alerts from metrics and policy.
Disabled unless LIVE_IO_ALLOWED=true; thresholds conservative.
"""

from __future__ import annotations

import os
from typing import Any, Dict, List


def _live_io_allowed() -> bool:
    return os.environ.get("LIVE_IO_ALLOWED", "").strip().lower() in ("1", "true", "yes")


DEFAULT_POLICY: Dict[str, Any] = {
    "enabled": None,  # None = derive from LIVE_IO_ALLOWED
    "max_failure_rate": 0.2,
    "max_p95_latency_ms": 5000,
    "max_timeouts_per_run": 5,
    "max_rate_limited_per_run": 3,
}


def evaluate(metrics: Dict[str, Any], policy: Dict[str, Any] | None = None) -> List[Dict[str, Any]]:
    """
    Evaluate guardrails on live IO metrics. Returns list of alerts:
    { "code": str, "severity": "INFO"|"WARN"|"CRITICAL", "message": str }.
    Policy: disabled unless LIVE_IO_ALLOWED=true; thresholds conservative.
    """
    policy = policy or DEFAULT_POLICY
    enabled = policy.get("enabled")
    if enabled is None:
        enabled = _live_io_allowed()
    if not enabled:
        return []

    alerts: List[Dict[str, Any]] = []
    counters = metrics.get("counters") or {}
    latency_ms = metrics.get("latency_ms") or {}

    requests_total = int(counters.get("requests_total", 0))
    failures_total = int(counters.get("failures_total", 0))
    timeouts_total = int(counters.get("timeouts_total", 0))
    rate_limited_total = int(counters.get("rate_limited_total", 0))
    p95 = float(latency_ms.get("p95", 0))

    max_failure_rate = float(policy.get("max_failure_rate", DEFAULT_POLICY["max_failure_rate"]))
    max_p95_ms = float(policy.get("max_p95_latency_ms", DEFAULT_POLICY["max_p95_latency_ms"]))
    max_timeouts = int(policy.get("max_timeouts_per_run", DEFAULT_POLICY["max_timeouts_per_run"]))
    max_rate_limited = int(policy.get("max_rate_limited_per_run", DEFAULT_POLICY["max_rate_limited_per_run"]))

    if requests_total > 0:
        failure_rate = failures_total / requests_total
        if failure_rate > max_failure_rate:
            alerts.append({
                "code": "LIVE_IO_HIGH_FAILURE_RATE",
                "severity": "WARN",
                "message": f"Live IO failure rate {failure_rate:.1%} exceeds threshold {max_failure_rate:.1%}.",
            })

    if p95 > max_p95_ms and (latency_ms.get("count") or 0) > 0:
        alerts.append({
            "code": "LIVE_IO_HIGH_P95_LATENCY",
            "severity": "WARN",
            "message": f"Live IO p95 latency {p95:.0f} ms exceeds {max_p95_ms:.0f} ms.",
        })

    if timeouts_total > max_timeouts:
        alerts.append({
            "code": "LIVE_IO_TIMEOUTS",
            "severity": "WARN",
            "message": f"Live IO timeouts ({timeouts_total}) exceed threshold ({max_timeouts}).",
        })

    if rate_limited_total > max_rate_limited:
        alerts.append({
            "code": "LIVE_IO_RATE_LIMITED",
            "severity": "WARN",
            "message": f"Live IO rate-limited count ({rate_limited_total}) exceeds threshold ({max_rate_limited}).",
        })

    return alerts
