from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from repositories.raw_payload_repo import RawPayloadRepository


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
    """Retrieve cached payload from database.

    Returns:
        Normalized payload dict if found, None otherwise
    """
    repo = RawPayloadRepository(session)
    cache_key = _make_cache_key(match_id, domain, window_hours)

    # Check if payload exists by hash
    exists = await repo.exists_by_hash(cache_key)
    if not exists:
        return None

    # TODO: Implement retrieval of cached payload
    # For now, return None (cache miss) - full implementation would query
    # RawPayload by hash and parse payload_json
    return None


async def cache_payload(
    session: AsyncSession,
    match_id: str,
    domain: str,
    window_hours: int,
    payload: Dict[str, Any],
) -> None:
    """Cache a normalized payload in the database."""
    repo = RawPayloadRepository(session)
    cache_key = _make_cache_key(match_id, domain, window_hours)

    # Serialize payload to JSON
    payload_json = json.dumps(payload, default=str)

    # Store in RawPayload table
    await repo.add_payload(
        source_name="pipeline_cache",
        domain=domain,
        payload_hash=cache_key,
        payload_json=payload_json,
        related_match_id=match_id,
    )
