"""
Late-data replay scenario model (I1 Part A).
Simulation-only: no production behavior change.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict


class ScenarioType(str, Enum):
    """Type of late-data variant."""

    DELAYED_OBSERVED_AT = "DELAYED_OBSERVED_AT"
    MISSING_TIMING_TAGS = "MISSING_TIMING_TAGS"
    STALE_EFFECTIVE_FROM = "STALE_EFFECTIVE_FROM"


@dataclass
class ReplayScenario:
    """A single replay scenario: base snapshot + variant type + parameters."""

    scenario_id: str
    base_snapshot_id: str
    fixture_id: str
    scenario_type: ScenarioType
    parameters: Dict[str, Any]
    created_at_utc: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "scenario_id": self.scenario_id,
            "base_snapshot_id": self.base_snapshot_id,
            "fixture_id": self.fixture_id,
            "scenario_type": self.scenario_type.value,
            "parameters": self.parameters,
            "created_at_utc": self.created_at_utc,
        }
