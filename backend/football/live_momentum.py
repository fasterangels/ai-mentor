"""Live momentum engine: derive momentum signals from live stats."""
from __future__ import annotations

from dataclasses import dataclass

from .live_stats import LiveStats


@dataclass
class LiveMomentum:
    attacking_pressure_home: float
    attacking_pressure_away: float
    control_index_home: float
    control_index_away: float
    momentum_team: str
    momentum_strength: float


def compute_attacking_pressure(
    shots: int,
    shots_on_target: int,
    dangerous_attacks: int,
) -> float:
    return shots * 0.3 + shots_on_target * 0.5 + dangerous_attacks * 0.02


def compute_control_index(possession: float, corners: int) -> float:
    return possession * 0.7 + corners * 3


def build_live_momentum(stats: LiveStats) -> LiveMomentum:
    pressure_home = compute_attacking_pressure(
        stats.shots_home,
        stats.shots_on_target_home,
        stats.dangerous_attacks_home,
    )
    pressure_away = compute_attacking_pressure(
        stats.shots_away,
        stats.shots_on_target_away,
        stats.dangerous_attacks_away,
    )
    control_home = compute_control_index(stats.possession_home, stats.corners_home)
    control_away = compute_control_index(stats.possession_away, stats.corners_away)

    diff = pressure_home - pressure_away
    if diff > 0:
        team = "home"
    elif diff < 0:
        team = "away"
    else:
        team = "balanced"
    strength = abs(diff)

    return LiveMomentum(
        attacking_pressure_home=pressure_home,
        attacking_pressure_away=pressure_away,
        control_index_home=control_home,
        control_index_away=control_away,
        momentum_team=team,
        momentum_strength=strength,
    )
