"""Graduation Criteria v1: schema and fixed thresholds (measurement-only)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List

# Fixed thresholds (do not auto-tune)
DEFAULT_DELTA_COVERAGE_MIN_FIXTURES = 50
DEFAULT_DELTA_PAYLOAD_MATCH_MIN_RATE = 0.95
DEFAULT_STALENESS_MIN_REASON_CODES = 20
DEFAULT_DECAY_MIN_REASON_CODES = 20
DEFAULT_UNCERTAINTY_MIN_DECISIONS = 200
LATE_DATA_ACCURACY_DELTA_24H_MIN = -0.10
LATE_DATA_REFUSAL_DELTA_24H_MIN = 0.05
DEFAULT_WORST_CASE_MIN_ROWS = 20


@dataclass
class CriterionResult:
    """Result of one graduation criterion: name, pass/fail, optional details."""

    name: str
    pass_: bool
    details: Dict[str, Any]


@dataclass
class GraduationResult:
    """Overall graduation result: overall_pass (AND of all), criteria list, computed_at_utc."""

    overall_pass: bool
    criteria: List[CriterionResult]
    computed_at_utc: datetime
