"""Live awareness state v1: informational only; no action, no behavior change."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class LiveAwarenessState:
    """
    Summary of live_shadow existence and freshness for a scope (e.g. fixture).
    Informational only; not used for activation or analysis decisions.
    """

    schema_version: int
    computed_at_utc: datetime
    scope_id: str
    has_live_shadow: bool
    latest_live_observed_at_utc: Optional[str]
    latest_recorded_observed_at_utc: Optional[str]
    observed_gap_ms: Optional[int]
    notes: Optional[str]
