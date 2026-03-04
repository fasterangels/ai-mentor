"""
Structured ops events for pipeline milestones and guardrails.
Log-level + structured event dict; deterministic (no random ids).
Timestamps only in log output, not in deterministic report artifacts.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Dict

OPS_LOGGER_NAME = "ops_events"


def _logger() -> logging.Logger:
    return logging.getLogger(OPS_LOGGER_NAME)


def _event(event_type: str, **kwargs: Any) -> None:
    """Emit a structured ops event (deterministic keys; no random ids)."""
    msg = f"ops_event={event_type} " + " ".join(f"{k}={v!r}" for k, v in sorted(kwargs.items()))
    _logger().info(msg, extra={"ops_event_type": event_type, "ops_event": {**kwargs}})


def log_pipeline_start(connector_name: str, match_id: str) -> float:
    """Log pipeline start; return start time for duration calculation."""
    _event("pipeline_start", connector_name=connector_name, match_id=match_id)
    return time.perf_counter()


def log_pipeline_end(
    connector_name: str,
    match_id: str,
    duration_seconds: float,
    error: str | None = None,
) -> None:
    """Log pipeline end with duration (deterministic)."""
    payload: Dict[str, Any] = {
        "connector_name": connector_name,
        "match_id": match_id,
        "duration_seconds": round(duration_seconds, 4),
    }
    if error:
        payload["error"] = error
    _event("pipeline_end", **payload)


def log_ingestion_source(
    connector_name: str,
    source: str,
    match_id: str,
) -> None:
    """Log ingestion source used (recorded vs live). source must be 'recorded' or 'live'."""
    _event("ingestion_source", connector_name=connector_name, source=source, match_id=match_id)


def log_evaluation_summary(
    match_count: int,
    resolved_count: int,
    accuracy_by_market: Dict[str, float] | None = None,
) -> None:
    """Log evaluation summary (counts, optional accuracy). Deterministic."""
    payload: Dict[str, Any] = {"match_count": match_count, "resolved_count": resolved_count}
    if accuracy_by_market is not None:
        payload["accuracy_by_market"] = {k: round(v, 4) for k, v in sorted(accuracy_by_market.items())}
    _event("evaluation_summary", **payload)


def log_guardrail_trigger(
    trigger: str,
    detail: str,
    cap_value: int | float | None = None,
) -> None:
    """Log guardrail trigger (caps hit, live_io blocked, etc.)."""
    payload: Dict[str, Any] = {"trigger": trigger, "detail": detail}
    if cap_value is not None:
        payload["cap_value"] = cap_value
    _event("guardrail_trigger", **payload)


def log_refusal_opt_start(reports_dir: str) -> None:
    """Log refusal optimization run start."""
    _event("refusal_opt_start", reports_dir=reports_dir)


def log_refusal_opt_end(
    reports_dir: str,
    duration_seconds: float,
    decisions_count: int,
    artifacts_written: int,
) -> None:
    """Log refusal optimization run end."""
    _event(
        "refusal_opt_end",
        reports_dir=reports_dir,
        duration_seconds=round(duration_seconds, 4),
        decisions_count=decisions_count,
        artifacts_written=artifacts_written,
    )


def log_refusal_opt_written(artifact_paths: list) -> None:
    """Log refusal optimization artifacts written."""
    _event("refusal_opt_written", artifact_paths=artifact_paths)


def log_refusal_opt_missing_inputs(detail: str) -> None:
    """Log when uncertainty-shadow or evaluation inputs are missing."""
    _event("refusal_opt_missing_inputs", detail=detail)
