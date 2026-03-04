from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple

from .models import Injury


@dataclass
class InjuryImpact:
    injury_count: int
    suspension_count: int
    injury_impact_score: float
    availability: float


def compute_injury_counts(injuries: List[Injury]) -> Tuple[int, int]:
    injury_count = 0
    suspension_count = 0
    for i in injuries:
        if i.type == "injury":
            injury_count += 1
        elif i.type == "suspension":
            suspension_count += 1
    return injury_count, suspension_count


def compute_impact(injury_count: int, suspension_count: int) -> float:
    impact = injury_count * 0.08 + suspension_count * 0.1
    return min(impact, 0.5)


def compute_availability(injury_count: int) -> float:
    availability = 1 - (injury_count * 0.05)
    return max(availability, 0.5)


def build_injury_impact(team_id: str, injuries: List[Injury]) -> InjuryImpact:
    team_injuries = [i for i in injuries if i.team_id == team_id]
    injury_count, suspension_count = compute_injury_counts(team_injuries)
    impact = compute_impact(injury_count, suspension_count)
    availability = compute_availability(injury_count)
    return InjuryImpact(
        injury_count=injury_count,
        suspension_count=suspension_count,
        injury_impact_score=impact,
        availability=availability,
    )
