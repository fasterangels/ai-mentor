"""
Uncertainty detection (H3): read-only signals. No refusals enforced; measurement only.
"""

from modeling.uncertainty.model import (
    UncertaintyProfile,
    UncertaintySignal,
)
from modeling.uncertainty.compute import (
    compute_uncertainty_profile,
    LOW_EFFECTIVE_CONFIDENCE_THRESHOLD,
    STALE_EVIDENCE_BANDS,
)

__all__ = [
    "UncertaintyProfile",
    "UncertaintySignal",
    "compute_uncertainty_profile",
    "LOW_EFFECTIVE_CONFIDENCE_THRESHOLD",
    "STALE_EVIDENCE_BANDS",
]
