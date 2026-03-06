from __future__ import annotations

from dataclasses import dataclass
from typing import List

from .models import LastMatch


@dataclass
class TeamIntelligence:
    team_id: str
    form_score: float
    momentum: float
    motivation: str
    pressure: float


def compute_form_score(matches: List[LastMatch]) -> float:
    score = 0
    for m in matches:
        if m.result == "W":
            score += 3
        elif m.result == "D":
            score += 1
    return score / (len(matches) * 3) if matches else 0


def compute_momentum(matches: List[LastMatch]) -> float:
    momentum = 0
    weight = 1
    for m in reversed(matches):
        if m.result == "W":
            momentum += weight
        elif m.result == "L":
            momentum -= weight
        weight += 1
    return momentum


def estimate_pressure(position: int, total_teams: int) -> float:
    if position <= 3:
        return 0.7
    if position >= total_teams - 3:
        return 0.9
    return 0.3


def estimate_motivation(position: int, total_teams: int) -> str:
    if position <= 2:
        return "title_race"
    if position <= 6:
        return "europe"
    if position >= total_teams - 3:
        return "relegation_fight"
    return "mid_table"


def build_team_intelligence(
    team_id: str,
    last_matches: List[LastMatch],
    position: int = 10,
    total_teams: int = 20,
) -> TeamIntelligence:
    return TeamIntelligence(
        team_id=team_id,
        form_score=compute_form_score(last_matches),
        momentum=compute_momentum(last_matches),
        motivation=estimate_motivation(position, total_teams),
        pressure=estimate_pressure(position, total_teams),
    )
