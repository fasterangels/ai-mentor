"""Pydantic policy model and versioning."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class PolicyVersion(BaseModel):
    version: str
    created_at_utc: datetime
    notes: str | None = None


class MarketPolicy(BaseModel):
    min_confidence: float = Field(..., ge=0.0, le=1.0)
    confidence_bands: list[tuple[float, float]] | None = None


class ReasonPolicy(BaseModel):
    reason_code: str
    dampening_factor: float = Field(default=1.0, ge=0.0, le=1.0)


class Policy(BaseModel):
    meta: PolicyVersion
    markets: dict[str, MarketPolicy]
    reasons: dict[str, ReasonPolicy] = Field(default_factory=dict)
