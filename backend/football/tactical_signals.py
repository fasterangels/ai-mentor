from __future__ import annotations

from dataclasses import dataclass
from typing import List

from .models import H2HItem, LastMatch


@dataclass
class TacticalSignals:
    attacking_strength: float
    defensive_weakness: float
    goal_expectation: float
    match_tempo: float


def compute_attacking_strength(last_matches: List[LastMatch]) -> float:
    score = 0.0
    for m in last_matches:
        if m.result == "W":
            score += 1.0
        elif m.result == "D":
            score += 0.5
    return score / max(len(last_matches), 1)


def compute_defensive_weakness(last_matches: List[LastMatch]) -> float:
    weakness = 0.0
    for m in last_matches:
        if m.result == "L":
            weakness += 1.0
    return weakness / max(len(last_matches), 1)


def compute_goal_expectation(h2h: List[H2HItem]) -> float:
    if not h2h:
        return 2.4
    goals = [h.home_goals + h.away_goals for h in h2h]
    return sum(goals) / len(goals)


def compute_match_tempo(last_home: List[LastMatch], last_away: List[LastMatch]) -> float:
    total = len(last_home) + len(last_away)
    if total == 0:
        return 0.5
    wins = sum(1 for m in last_home + last_away if m.result == "W")
    return wins / total


def build_tactical_signals(
    last_home: List[LastMatch],
    last_away: List[LastMatch],
    h2h: List[H2HItem],
) -> TacticalSignals:
    atk = compute_attacking_strength(last_home)
    defw = compute_defensive_weakness(last_away)
    goals = compute_goal_expectation(h2h)
    tempo = compute_match_tempo(last_home, last_away)
    return TacticalSignals(
        attacking_strength=atk,
        defensive_weakness=defw,
        goal_expectation=goals,
        match_tempo=tempo,
    )
