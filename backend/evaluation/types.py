"""Types for evaluation and KPI reporting."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict

# Outcome labels per market
OUTCOME_HIT = "HIT"
OUTCOME_MISS = "MISS"
OUTCOME_NA = "N/A"

# Period types for KPI aggregation
PERIOD_DAY = "DAY"
PERIOD_WEEK = "WEEK"
PERIOD_MONTH = "MONTH"


@dataclass
class MarketOutcome:
    """Outcome for a single market (HIT, MISS, or N/A)."""

    market: str
    outcome: str  # OUTCOME_HIT | OUTCOME_MISS | OUTCOME_NA


@dataclass
class EvaluationResult:
    """Result of evaluating a single prediction against final scores."""

    status: str  # "EVALUATED" | "PENDING"
    market_results: Dict[str, str] = field(default_factory=dict)  # market -> HIT | MISS | N/A


@dataclass
class KPIReport:
    """Aggregated KPIs for a time period."""

    period: str  # "DAY" | "WEEK" | "MONTH"
    reference_date_utc: datetime
    total_predictions: int
    hits: int
    misses: int
    hit_rate: float  # 0.0 - 1.0
    miss_rate: float  # 0.0 - 1.0
