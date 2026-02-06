"""
Live shadow read adapter (G1): read live -> write snapshots only. No analysis, no decisions.
Requires LIVE_IO_ALLOWED=true and SNAPSHOT_WRITES_ALLOWED=true. Fail-fast when disabled.
"""

from __future__ import annotations

import hashlib
import json
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from ingestion.live_io import (
    LiveIODisabledError,
    live_io_allowed,
    snapshot_writes_allowed,
)
from pipeline.live_snapshot.live_source_client import LiveSourceClient
from repositories.raw_payload_repo import RawPayloadRepository

from ops.ops_events import (
    log_live_shadow_blocked_by_flag,
    log_live_shadow_fetch_failed,
    log_live_shadow_fetch_ok,
    log_live_shadow_ingestion_end,
    log_live_shadow_ingestion_start,
)

LIVE_SHADOW_SOURCE_NAME = "live_shadow"
LIVE_SHADOW_DOMAIN = "fixture_detail"


def _canonical_payload(payload: Dict[str, Any]) -> str:
    """Stable JSON for hashing (sorted keys)."""
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)


def _payload_checksum(payload: Dict[str, Any]) -> str:
    """SHA-256 of canonical payload for dedup."""
    return hashlib.sha256(_canonical_payload(payload).encode("utf-8")).hexdigest()


async def run_live_shadow_read(
    session: AsyncSession,
    client: LiveSourceClient,
    *,
    source_name: str = "live_shadow",
    now_utc: Optional[datetime] = None,
) -> Dict[str, Any]:
    """
    Run live-shadow read: fetch from client, write snapshots to RawPayload store. No analysis.
    If LIVE_IO_ALLOWED or SNAPSHOT_WRITES_ALLOWED is false: emit live_shadow_blocked_by_flag and return
    with error. Returns summary: snapshots_written, deduped, fetch_ok, fetch_failed, error (if blocked).
    """
    if not live_io_allowed():
        log_live_shadow_blocked_by_flag(
            "LIVE_IO_ALLOWED is not true; set LIVE_IO_ALLOWED=true to run live-shadow"
        )
        return {
            "snapshots_written": 0,
            "deduped": 0,
            "fetch_ok": 0,
            "fetch_failed": 0,
            "error": "LIVE_IO_NOT_ALLOWED",
            "detail": "LIVE_IO_ALLOWED is not true.",
        }
    if not snapshot_writes_allowed():
        log_live_shadow_blocked_by_flag(
            "SNAPSHOT_WRITES_ALLOWED is not true; set SNAPSHOT_WRITES_ALLOWED=true to write snapshots"
        )
        return {
            "snapshots_written": 0,
            "deduped": 0,
            "fetch_ok": 0,
            "fetch_failed": 0,
            "error": "SNAPSHOT_WRITES_NOT_ALLOWED",
            "detail": "SNAPSHOT_WRITES_ALLOWED is not true.",
        }

    now = now_utc or datetime.now(timezone.utc)
    repo = RawPayloadRepository(session)
    snapshots_written = 0
    deduped = 0
    fetch_ok = 0
    fetch_failed = 0

    try:
        fixtures = client.fetch_fixtures()
    except Exception as e:
        log_live_shadow_fetch_failed("_list", str(e))
        log_live_shadow_ingestion_end(0.0, 0, 0, 0, 1)
        return {
            "snapshots_written": 0,
            "deduped": 0,
            "fetch_ok": 0,
            "fetch_failed": 1,
            "error": "FETCH_FAILED",
            "detail": str(e),
        }

    t_start = log_live_shadow_ingestion_start(len(fixtures))

    for raw in fixtures:
        fixture_id = str(raw.get("fixture_id") or raw.get("match_id") or raw.get("id") or "unknown")
        fetch_started = datetime.now(timezone.utc)
        try:
            payload = dict(raw)
        except Exception as e:
            log_live_shadow_fetch_failed(fixture_id, str(e))
            fetch_failed += 1
            continue
        fetch_ended = datetime.now(timezone.utc)
        latency_ms = (fetch_ended - fetch_started).total_seconds() * 1000
        log_live_shadow_fetch_ok(fixture_id, latency_ms)
        fetch_ok += 1

        checksum = _payload_checksum(payload)
        if await repo.exists_by_hash(checksum):
            deduped += 1
            continue

        envelope: Dict[str, Any] = {
            "metadata": {
                "snapshot_type": "live_shadow",
                "source": {
                    "class": "LIVE_SHADOW",
                    "name": source_name,
                    "ref": None,
                    "reliability_tier": "MED",
                },
                "observed_at": now.isoformat(),
                "checksum": checksum,
                "latency_ms": round(latency_ms, 2),
                "fetch_started_at": fetch_started.isoformat(),
                "fetch_ended_at": fetch_ended.isoformat(),
            },
            "payload": payload,
        }
        payload_json = json.dumps(envelope, sort_keys=True, separators=(",", ":"), default=str)
        await repo.add_payload(
            source_name=LIVE_SHADOW_SOURCE_NAME,
            domain=LIVE_SHADOW_DOMAIN,
            payload_hash=checksum,
            payload_json=payload_json,
            related_match_id=None,
        )
        snapshots_written += 1

    duration = time.perf_counter() - t_start
    log_live_shadow_ingestion_end(duration, snapshots_written, deduped, fetch_ok, fetch_failed)

    return {
        "snapshots_written": snapshots_written,
        "deduped": deduped,
        "fetch_ok": fetch_ok,
        "fetch_failed": fetch_failed,
    }


def run_live_shadow_read_blocked_or_raise() -> None:
    """
    When live-shadow mode is requested but flags are off: raise LiveIODisabledError (fail-fast).
    """
    if not live_io_allowed():
        log_live_shadow_blocked_by_flag("LIVE_IO_ALLOWED is not true")
        raise LiveIODisabledError(
            "Live-shadow mode requires LIVE_IO_ALLOWED=true. Set LIVE_IO_ALLOWED=true to run."
        )
    if not snapshot_writes_allowed():
        log_live_shadow_blocked_by_flag("SNAPSHOT_WRITES_ALLOWED is not true")
        raise LiveIODisabledError(
            "Live-shadow mode requires SNAPSHOT_WRITES_ALLOWED=true to write snapshots. Set SNAPSHOT_WRITES_ALLOWED=true."
        )
