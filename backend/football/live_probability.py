"""Live probability update: adjust pre-match probs using momentum and live stats."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict


@dataclass
class LiveProbability:
    home_prob: float
    draw_prob: float
    away_prob: float


def normalize(a: float, b: float, c: float) -> tuple[float, float, float]:
    s = a + b + c
    if s == 0:
        return 0.33, 0.33, 0.33
    return a / s, b / s, c / s


def update_live_probability(
    pre_match: Dict[str, Any],
    momentum: Dict[str, Any],
    stats: Dict[str, Any],
) -> LiveProbability:
    home = pre_match["home_prob"]
    draw = pre_match["draw_prob"]
    away = pre_match["away_prob"]

    momentum_team = momentum.get("momentum_team", "balanced")
    strength = momentum.get("momentum_strength", 0)

    shots_home = stats.get("shots_home", 0)
    shots_away = stats.get("shots_away", 0)

    adjustment = strength * 0.01

    if momentum_team == "home":
        home += adjustment
        away -= adjustment
    elif momentum_team == "away":
        away += adjustment
        home -= adjustment

    if shots_home > shots_away:
        home += 0.01
    elif shots_away > shots_home:
        away += 0.01

    home = max(0.0, home)
    draw = max(0.0, draw)
    away = max(0.0, away)
    home, draw, away = normalize(home, draw, away)

    return LiveProbability(
        home_prob=home,
        draw_prob=draw,
        away_prob=away,
    )
