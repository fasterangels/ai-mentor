"""
Compute live awareness state from stored snapshots (read-only).
No action, no behavior change. Deterministic: same stored inputs -> same outputs.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from pipeline.snapshot_envelope import parse_payload_json, _parse_iso
from repositories.raw_payload_repo import RawPayloadRepository

from .model import LiveAwarenessState


def _observed_at_from_payload_json(payload_json: str, fetched_at_utc: datetime) -> str | None:
    """Extract observed_at_utc from payload_json envelope; legacy fallback to created_at_utc."""
    meta, _ = parse_payload_json(payload_json, created_at_utc_fallback=fetched_at_utc)
    return meta.get("observed_at_utc") or meta.get("observed_at") or meta.get("effective_from_utc")


async def _latest_observed_utc(
    session: AsyncSession,
    source_name: str,
    fixture_id: str,
) -> str | None:
    """Return latest observed_at_utc (ISO str) for the given source and fixture, or None."""
    repo = RawPayloadRepository(session)
    rows = await repo.list_rows_by_source_and_match_id(source_name, fixture_id)
    if not rows:
        return None
    best: str | None = None
    for row in rows:
        observed = _observed_at_from_payload_json(row.payload_json, row.fetched_at_utc)
        if not observed:
            continue
        if best is None:
            best = observed
            continue
        dt_best = _parse_iso(best)
        dt_obs = _parse_iso(observed)
        if dt_best is None:
            best = observed
            continue
        if dt_obs is None:
            continue
        if dt_obs.tzinfo is None:
            dt_obs = dt_obs.replace(tzinfo=timezone.utc)
        if dt_best.tzinfo is None:
            dt_best = dt_best.replace(tzinfo=timezone.utc)
        if dt_obs > dt_best:
            best = observed
    return best


async def compute_live_awareness(
    session: AsyncSession,
    scope: str,
    computed_at_utc: datetime | None = None,
) -> LiveAwarenessState:
    """
    Compute live awareness state for the given scope (fixture_id).
    Read-only: queries stored snapshots only. No activation, no analysis changes.
    - If no live_shadow snapshots: has_live_shadow=False, gaps null.
    - If both live and recorded present: observed_gap_ms = latest_live - latest_recorded (ms).
    """
    if computed_at_utc is None:
        computed_at_utc = datetime.now(timezone.utc)
    if computed_at_utc.tzinfo is None:
        computed_at_utc = computed_at_utc.replace(tzinfo=timezone.utc)

    fixture_id = scope
    latest_live = await _latest_observed_utc(session, "live_shadow", fixture_id)
    latest_recorded = await _latest_observed_utc(session, "pipeline_cache", fixture_id)

    has_live_shadow = latest_live is not None
    observed_gap_ms: int | None = None
    notes: str | None = None

    if latest_live and latest_recorded:
        dt_live = _parse_iso(latest_live)
        dt_rec = _parse_iso(latest_recorded)
        if dt_live and dt_rec:
            if dt_live.tzinfo is None:
                dt_live = dt_live.replace(tzinfo=timezone.utc)
            if dt_rec.tzinfo is None:
                dt_rec = dt_rec.replace(tzinfo=timezone.utc)
            delta = dt_live - dt_rec
            observed_gap_ms = int(delta.total_seconds() * 1000)
    elif not has_live_shadow:
        notes = "no live_shadow snapshots"

    return LiveAwarenessState(
        schema_version=1,
        computed_at_utc=computed_at_utc,
        scope_id=fixture_id,
        has_live_shadow=has_live_shadow,
        latest_live_observed_at_utc=latest_live,
        latest_recorded_observed_at_utc=latest_recorded,
        observed_gap_ms=observed_gap_ms,
        notes=notes,
    )
