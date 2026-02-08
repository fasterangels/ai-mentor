"""
Reason time-decay model (H1): piecewise penalty by age band.
Measurement-only; fitted params and reports only. Not applied to analyzer.
"""

from modeling.reason_decay.model import (
    DecayModelParams,
    FitDiagnostics,
    MODEL_TYPE_PIECEWISE_V1,
    SCHEMA_VERSION,
)
from modeling.reason_decay.fit_piecewise import (
    MIN_SUPPORT,
    fit_piecewise_decay,
)

__all__ = [
    "DecayModelParams",
    "FitDiagnostics",
    "MODEL_TYPE_PIECEWISE_V1",
    "SCHEMA_VERSION",
    "MIN_SUPPORT",
    "fit_piecewise_decay",
]
