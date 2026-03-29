"""
Confidence penalty (H2): read-only computation from staleness + decay params.
No effect applied yet; not used in analyzer or production path.
"""

from modeling.confidence_penalty.model import (
    PenaltyResult,
    compute_penalty,
)

__all__ = [
    "PenaltyResult",
    "compute_penalty",
]
