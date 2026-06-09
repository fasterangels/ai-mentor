"""
Staleness metrics (G4): measurement-only metrics by (market, reason_code, age_band).
No decay, no policy. Deterministic aggregation.
"""

from __future__ import annotations

from evaluation.staleness_metrics.age_bands import band_for_age_ms
from evaluation.staleness_metrics.aggregate import compute_staleness_metrics
from evaluation.staleness_metrics.model import StalenessReport, StalenessRow

__all__ = [
    "band_for_age_ms",
    "compute_staleness_metrics",
    "StalenessReport",
    "StalenessRow",
]
