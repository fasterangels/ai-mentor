"""
Staleness metrics (G4): measurement-only metrics by (market, reason_code, age_band).
No decay, no policy. Deterministic. Backward compatible with legacy snapshots.
"""

from __future__ import annotations

from .run import (
    MARKETS,
    StalenessRow,
    _aggregate_staleness_rows,
    run_staleness_evaluation,
)

__all__ = [
    "MARKETS",
    "StalenessRow",
    "_aggregate_staleness_rows",
    "run_staleness_evaluation",
]
