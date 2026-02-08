"""
Live awareness run mode: compute LiveAwarenessState for a fixture, write live_awareness.json and live_awareness.md.
No action: does not trigger ingestion, analysis, or decisions. Explicit mode only; must NOT run by default.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Dict

from sqlalchemy.ext.asyncio import AsyncSession

from live_awareness import compute_live_awareness
from live_awareness.reporting import write_live_awareness_json, write_live_awareness_md
from ops.ops_events import (
    log_live_awareness_end,
    log_live_awareness_start,
    log_live_awareness_written,
)

MODE_LIVE_AWARENESS = "live-awareness"

LIVE_AWARENESS_JSON = "live_awareness.json"
LIVE_AWARENESS_MD = "live_awareness.md"


async def run_live_awareness(
    session: AsyncSession,
    reports_dir: str | Path,
    fixture_id: str,
) -> Dict[str, Any]:
    """
    Compute live awareness for the given fixture_id, write artifacts, emit ops events.
    Returns summary: error (if any), json_path, md_path, has_live_shadow, observed_gap_ms.
    """
    reports_path = Path(reports_dir)
    t0 = log_live_awareness_start(fixture_id)
    try:
        state = await compute_live_awareness(session, fixture_id)
    except Exception as e:
        log_live_awareness_end(fixture_id=fixture_id, has_live_shadow=False, duration_seconds=time.perf_counter() - t0)
        return {
            "error": str(e),
            "json_path": None,
            "md_path": None,
            "has_live_shadow": False,
            "observed_gap_ms": None,
        }

    reports_path.mkdir(parents=True, exist_ok=True)
    json_path = reports_path / LIVE_AWARENESS_JSON
    md_path = reports_path / LIVE_AWARENESS_MD

    write_live_awareness_json(state, json_path)
    write_live_awareness_md(state, md_path)

    log_live_awareness_written(str(json_path), str(md_path))
    log_live_awareness_end(
        fixture_id=fixture_id,
        has_live_shadow=state.has_live_shadow,
        duration_seconds=time.perf_counter() - t0,
    )

    return {
        "error": None,
        "json_path": str(json_path),
        "md_path": str(md_path),
        "has_live_shadow": state.has_live_shadow,
        "observed_gap_ms": state.observed_gap_ms,
    }
