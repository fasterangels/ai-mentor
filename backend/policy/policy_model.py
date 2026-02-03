"""Pydantic policy model and versioning."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class PolicyVersion(BaseModel):
    """Policy version metadata."""

    version: str
    created_at_utc: datetime
    notes: str | None = None


class MarketPolicy(BaseModel):
    """Per-market thresholds."""

    min_confidence: float = Field(..., ge=0.0, le=1.0)
    confidence_bands: list[tuple[float, float]] | None = None  # optional, for reporting


class ReasonPolicy(BaseModel):
    """Per-reason dampening."""

    reason_code: str
    dampening_factor: float = Field(default=1.0, ge=0.0, le=1.0)


class Policy(BaseModel):
    """Root policy: version + markets + reasons."""

    meta: PolicyVersion
    markets: dict[str, MarketPolicy]  # keys: one_x_two, over_under_25, gg_ng
    reasons: dict[str, ReasonPolicy] = Field(default_factory=dict)  # keyed by reason_code

    def model_dump_sorted(self, **kwargs: Any) -> dict[str, Any]:
        """Dump for stable JSON (sorted keys)."""
        return self.model_dump(mode="json", **kwargs)
