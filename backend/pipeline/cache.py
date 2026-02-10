from __future__ import annotations

import hashlib
import json
import time
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from pipeline.snapshot_envelope import build_envelope_for_recorded, parse_payload_json
from repositories.raw_payload_repo import RawPayloadRepository
from ops.ops_events import (
    log_snapshot_envelope_missing_fields,
    log_snapshot_integrity_check_failed,
    log_snapshot_write_end,
    log_snapshot_write_start,
)


def _make_cache_key(match_id: str, domain: str, window_hours: int) -> str:
    """Generate cache key for (match_id, domain, window_hours)."""
    key_str = f"{match_id}:{domain}:{window_hours}"
    return hashlib.sha256(key_str.encode()).hexdigest()[:16]


async def get_cached_payload(
    session: AsyncSession,
    match_id: str,
    domain: str,
    window_hours: int,
) -> Optional[Dict[str, Any]]:
    """Retrieve cached payload from database. Backward compatible: legacy payload_json parsed with defaults."""
    repo = RawPayloadRepository(session)
    cache_key = _make_cache_key(match_id, domain, window_hours)
    row = await repo.get_by_hash(cache_key)
    if row is None:
        return None
    created_fallback = row.fetched_at_utc if row.fetched_at_utc.tzinfo else None
    meta, payload = parse_payload_json(
        row.payload_json,
        created_at_utc_fallback=created_fallback,
        on_missing_fields=log_snapshot_envelope_missing_fields,
        on_integrity_failed=log_snapshot_integrity_check_failed,
    )
    return payload if payload else None


async def cache_payload(
    session: AsyncSession,
    match_id: str,
    domain: str,
    window_hours: int,
    payload: Dict[str, Any],
) -> None:
    """Cache a normalized payload with G2 envelope (recorded, provenance + timing)."""
    repo = RawPayloadRepository(session)
    cache_key = _make_cache_key(match_id, domain, window_hours)
    now = datetime.now(timezone.utc)
    envelope = build_envelope_for_recorded(
        payload=payload,
        snapshot_id=cache_key,
        created_at_utc=now,
        source_name="pipeline_cache",
    )
    envelope_dict = envelope.to_dict()
    payload_json = json.dumps(
        {"metadata": envelope_dict, "payload": payload},
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    t_start = log_snapshot_write_start("recorded", cache_key)
    await repo.add_payload(
        source_name="pipeline_cache",
        domain=domain,
        payload_hash=cache_key,
        payload_json=payload_json,
        related_match_id=match_id,
    )
    log_snapshot_write_end("recorded", cache_key, time.perf_counter() - t_start)
