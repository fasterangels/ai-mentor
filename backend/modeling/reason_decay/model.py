"""
Reason decay model data structures (H1). Piecewise penalty by age band.
Measurement-only; not applied to analyzer. Stable JSON serialization.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List

# Schema and type identifiers for stable serialization
SCHEMA_VERSION = "1"
MODEL_TYPE_PIECEWISE_V1 = "PIECEWISE_V1"

# Band order must match G4 age_bands (youngest to oldest)
BAND_ORDER = [
    "0-30m",
    "30m-2h",
    "2h-6h",
    "6h-24h",
    "1d-3d",
    "3d-7d",
    "7d+",
]


@dataclass
class FitDiagnostics:
    """Simple fit quality metrics: coverage per band, optional MSE vs observed."""
    bands_with_support: int  # count of bands with total >= MIN_SUPPORT
    total_bands: int
    coverage_counts: List[int]  # total per band in same order as BAND_ORDER
    mse_vs_baseline: float | None = None  # optional: mean squared error of penalty vs observed drop

    def to_dict(self) -> Dict[str, Any]:
        return {
            "bands_with_support": self.bands_with_support,
            "coverage_counts": list(self.coverage_counts),
            "mse_vs_baseline": self.mse_vs_baseline,
            "total_bands": self.total_bands,
        }


@dataclass
class DecayModelParams:
    """
    Fitted decay model per (market, reason_code).
    Piecewise penalty by age band; monotonic non-increasing in age.
    """
    schema_version: str = SCHEMA_VERSION
    model_type: str = MODEL_TYPE_PIECEWISE_V1
    market: str = ""
    reason_code: str = ""
    bands: List[str] = field(default_factory=lambda: list(BAND_ORDER))
    penalty_by_band: List[float] = field(default_factory=list)  # 0..1, same order as bands
    fitted_at_utc: str = ""
    fit_quality: FitDiagnostics | None = None

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "bands": list(self.bands),
            "fit_quality": self.fit_quality.to_dict() if self.fit_quality else None,
            "fitted_at_utc": self.fitted_at_utc,
            "market": self.market,
            "model_type": self.model_type,
            "penalty_by_band": [round(p, 4) for p in self.penalty_by_band],
            "reason_code": self.reason_code,
            "schema_version": self.schema_version,
        }
        return d

    def to_json(self) -> str:
        """Stable JSON with sorted keys."""
        return json.dumps(self.to_dict(), sort_keys=True, indent=2, default=str)


def params_from_dict(d: Dict[str, Any]) -> DecayModelParams:
    """Deserialize from dict (e.g. JSON load)."""
    fq = d.get("fit_quality")
    if isinstance(fq, dict):
        fq = FitDiagnostics(
            bands_with_support=fq.get("bands_with_support", 0),
            total_bands=fq.get("total_bands", len(BAND_ORDER)),
            coverage_counts=fq.get("coverage_counts") or [],
            mse_vs_baseline=fq.get("mse_vs_baseline"),
        )
    else:
        fq = None
    return DecayModelParams(
        schema_version=d.get("schema_version", SCHEMA_VERSION),
        model_type=d.get("model_type", MODEL_TYPE_PIECEWISE_V1),
        market=d.get("market", ""),
        reason_code=d.get("reason_code", ""),
        bands=list(d.get("bands") or BAND_ORDER),
        penalty_by_band=[float(x) for x in (d.get("penalty_by_band") or [])],
        fitted_at_utc=d.get("fitted_at_utc", ""),
        fit_quality=fq,
    )
