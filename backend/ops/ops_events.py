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


def log_evidence_ingestion_start(fixture_id: str, item_count: int) -> float:
    """Log evidence ingestion start; return start time."""
    _event("evidence_ingestion_start", fixture_id=fixture_id, item_count=item_count)
    return time.perf_counter()


def log_evidence_ingestion_end(
    fixture_id: str,
    duration_seconds: float,
    items_written: int,
    deduped: int,
    conflict_detected: int,
) -> None:
    """Log evidence ingestion end with counts."""
    _event(
        "evidence_ingestion_end",
        fixture_id=fixture_id,
        duration_seconds=round(duration_seconds, 4),
        evidence_items_written=items_written,
        evidence_deduped=deduped,
        evidence_conflict_detected=conflict_detected,
    )


def log_live_shadow_blocked_by_flag(detail: str) -> None:
    """Emitted when live-shadow is requested but LIVE_IO_ALLOWED or SNAPSHOT_WRITES_ALLOWED is false."""
    _event("live_shadow_blocked_by_flag", detail=detail)


def log_live_shadow_ingestion_start(fixture_count: int) -> float:
    """Log live shadow ingestion start; return start time."""
    _event("live_shadow_ingestion_start", fixture_count=fixture_count)
    return time.perf_counter()


def log_live_shadow_ingestion_end(
    duration_seconds: float,
    snapshots_written: int,
    deduped: int,
    fetch_ok: int,
    fetch_failed: int,
) -> None:
    """Log live shadow ingestion end with counts."""
    _event(
        "live_shadow_ingestion_end",
        duration_seconds=round(duration_seconds, 4),
        live_shadow_snapshots_written=snapshots_written,
        live_shadow_deduped=deduped,
        fetch_ok=fetch_ok,
        fetch_failed=fetch_failed,
    )


def log_live_shadow_fetch_ok(fixture_id: str, latency_ms: float) -> None:
    """Emitted when a live fetch for one fixture succeeded."""
    _event("live_shadow_fetch_ok", fixture_id=fixture_id, latency_ms=round(latency_ms, 2))


def log_live_shadow_fetch_failed(fixture_id: str, reason: str) -> None:
    """Emitted when a live fetch for one fixture failed."""
    _event("live_shadow_fetch_failed", fixture_id=fixture_id, reason=reason)


def log_snapshot_write_start(snapshot_type: str, snapshot_id: str) -> float:
    """Log snapshot write start; return start time for duration."""
    _event("snapshot_write_start", snapshot_type=snapshot_type, snapshot_id=snapshot_id)
    return time.perf_counter()


def log_snapshot_write_end(
    snapshot_type: str,
    snapshot_id: str,
    duration_seconds: float,
) -> None:
    """Log snapshot write end with duration."""
    _event(
        "snapshot_write_end",
        snapshot_type=snapshot_type,
        snapshot_id=snapshot_id,
        duration_seconds=round(duration_seconds, 4),
    )


def log_snapshot_envelope_missing_fields(missing_keys: list) -> None:
    """Emitted when reading legacy snapshots and defaulting missing envelope fields."""
    _event("snapshot_envelope_missing_fields", missing_keys=missing_keys)


def log_snapshot_integrity_check_failed(
    snapshot_id: str,
    detail: str,
) -> None:
    """Emitted when envelope checksum mismatch detected. Does not fail pipeline by default."""
    _event("snapshot_integrity_check_failed", snapshot_id=snapshot_id, detail=detail)


def log_delta_eval_start() -> float:
    """Log delta evaluation start; return start time for duration."""
    _event("delta_eval_start")
    return time.perf_counter()


def log_delta_eval_end(
    reports_count: int,
    complete_count: int,
    incomplete_count: int,
    duration_seconds: float,
) -> None:
    """Log delta evaluation end with counts and duration."""
    _event(
        "delta_eval_end",
        reports_count=reports_count,
        complete_count=complete_count,
        incomplete_count=incomplete_count,
        duration_seconds=round(duration_seconds, 4),
    )


def log_delta_eval_incomplete(fixture_id: str, missing_side: str) -> None:
    """Emitted when one side (recorded or live_shadow) is missing for a fixture."""
    _event("delta_eval_incomplete", fixture_id=fixture_id, missing_side=missing_side)


def log_delta_eval_written(count: int) -> None:
    """Emitted when delta reports are written."""
    _event("delta_eval_written", count=count)


def log_staleness_eval_start() -> float:
    """Log staleness evaluation start; return start time for duration."""
    _event("staleness_eval_start")
    return time.perf_counter()


def log_staleness_eval_end(
    row_count: int,
    missing_timestamps_count: int,
    duration_seconds: float,
) -> None:
    """Log staleness evaluation end with counts and duration."""
    _event(
        "staleness_eval_end",
        row_count=row_count,
        missing_timestamps_count=missing_timestamps_count,
        duration_seconds=round(duration_seconds, 4),
    )


def log_staleness_eval_written(count: int) -> None:
    """Emitted when staleness metrics reports are written."""
    _event("staleness_eval_written", count=count)


def log_staleness_eval_missing_timestamps(count: int) -> None:
    """Emitted when legacy snapshots default (missing observed_at_utc)."""
    _event("staleness_eval_missing_timestamps", count=count)


def log_graduation_eval_start() -> float:
    """Log graduation evaluation start; return start time for duration."""
    _event("graduation_eval_start")
    return time.perf_counter()


def log_graduation_eval_end(
    overall_pass: bool,
    criteria_count: int,
    duration_seconds: float,
) -> None:
    """Log graduation evaluation end with result and duration."""
    _event(
        "graduation_eval_end",
        overall_pass=overall_pass,
        criteria_count=criteria_count,
        duration_seconds=round(duration_seconds, 4),
    )


def log_graduation_eval_written(json_path: str, md_path: str) -> None:
    """Emitted when graduation_result.json and graduation_result.md are written."""
    _event("graduation_eval_written", json_path=json_path, md_path=md_path)


def log_graduation_eval_failed_criteria(count: int) -> None:
    """Emitted when one or more criteria failed (count of failed)."""
    _event("graduation_eval_failed_criteria", count=count)
