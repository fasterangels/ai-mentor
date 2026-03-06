from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple

from .models import Injury, LineupPlayer


@dataclass
class LineupStrength:
    starters: int
    bench_players: int
    missing_players: int
    lineup_strength_score: float


def count_players(lineup: List[LineupPlayer], team_id: str) -> Tuple[int, int]:
    starters = 0
    bench = 0
    for p in lineup:
        if p.team_id != team_id:
            continue
        if p.role == "starter":
            starters += 1
        else:
            bench += 1
    return starters, bench


def count_missing_players(injuries: List[Injury], team_id: str) -> int:
    missing = 0
    for i in injuries:
        if i.team_id == team_id:
            missing += 1
    return missing


def compute_lineup_strength(starters: int, bench: int, missing: int) -> float:
    base = starters * 0.06 + bench * 0.02
    penalty = missing * 0.05
    score = base - penalty
    return max(min(score, 1.0), 0.0)


def build_lineup_strength(
    team_id: str,
    lineup: List[LineupPlayer],
    injuries: List[Injury],
) -> LineupStrength:
    starters, bench = count_players(lineup, team_id)
    missing = count_missing_players(injuries, team_id)
    score = compute_lineup_strength(starters, bench, missing)
    return LineupStrength(
        starters=starters,
        bench_players=bench,
        missing_players=missing,
        lineup_strength_score=score,
    )
