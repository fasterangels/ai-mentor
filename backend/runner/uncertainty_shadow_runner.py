"""
Uncertainty shadow runner (H3 Part B). Simulation only; no refusals enforced.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from sqlalchemy.ext.asyncio import AsyncSession

from evaluation.uncertainty_shadow import run_uncertainty_shadow


async def run_uncertainty_shadow_mode(
    session: AsyncSession,
    reports_dir: str | Path = "reports",
    **kwargs: Any,
) -> Dict[str, Any]:
    """Run uncertainty shadow: compute would_refuse per decision; write reports only."""
    return await run_uncertainty_shadow(session, reports_dir=reports_dir, **kwargs)
