"""
Live-shadow mode runner (G1): run only live read -> snapshot. No analysis, no evaluation.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from pipeline.live_snapshot.live_shadow_adapter import run_live_shadow_read
from pipeline.live_snapshot.live_source_client import LiveSourceClient


async def run_live_shadow_mode(
    session: AsyncSession,
    client: LiveSourceClient,
    *,
    source_name: str = "live_shadow",
    now_utc: Optional[Any] = None,
) -> Dict[str, Any]:
    """
    Run live-shadow only: fetch from client, write snapshots. No analyzer, no evaluator.
    """
    return await run_live_shadow_read(
        session,
        client,
        source_name=source_name,
        now_utc=now_utc,
    )
