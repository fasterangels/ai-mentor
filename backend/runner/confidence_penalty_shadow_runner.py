"""
Confidence penalty shadow runner (H2 Part B). SHADOW-ONLY reporting; no analyzer change.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from sqlalchemy.ext.asyncio import AsyncSession

from evaluation.confidence_penalty_shadow import run_confidence_penalty_shadow


async def run_confidence_penalty_shadow_mode(
    session: AsyncSession,
    reports_dir: str | Path = "reports",
    **kwargs: Any,
) -> Dict[str, Any]:
    """Run confidence penalty shadow: compute and report hypothetical penalties only."""
    return await run_confidence_penalty_shadow(session, reports_dir=reports_dir, **kwargs)
