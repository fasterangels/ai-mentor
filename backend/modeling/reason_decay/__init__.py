"""Reason decay model (H1): piecewise penalty by age band; deterministic fit."""

from __future__ import annotations

from .fit_piecewise import MIN_SUPPORT, fit_piecewise_decay
from .model import (
    BAND_ORDER,
    DecayModelParams,
    FitDiagnostics,
    MODEL_TYPE_PIECEWISE_V1,
    SCHEMA_VERSION,
    params_from_dict,
)

__all__ = [
    "BAND_ORDER",
    "DecayModelParams",
    "FitDiagnostics",
    "MIN_SUPPORT",
    "MODEL_TYPE_PIECEWISE_V1",
    "SCHEMA_VERSION",
    "fit_piecewise_decay",
    "params_from_dict",
]
