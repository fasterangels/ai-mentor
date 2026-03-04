"""Live match statistics interface (possession, shots, xG, etc.)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict


@dataclass
class LiveStats:
    possession_home: float
    possession_away: float
    shots_home: int
    shots_away: int
    shots_on_target_home: int
    shots_on_target_away: int
    corners_home: int
    corners_away: int
    dangerous_attacks_home: int
    dangerous_attacks_away: int
    xg_home: float
    xg_away: float


def build_live_stats(data: Dict[str, Any]) -> LiveStats:
    return LiveStats(
        possession_home=data.get("possession_home", 50),
        possession_away=data.get("possession_away", 50),
        shots_home=data.get("shots_home", 0),
        shots_away=data.get("shots_away", 0),
        shots_on_target_home=data.get("shots_on_target_home", 0),
        shots_on_target_away=data.get("shots_on_target_away", 0),
        corners_home=data.get("corners_home", 0),
        corners_away=data.get("corners_away", 0),
        dangerous_attacks_home=data.get("dangerous_attacks_home", 0),
        dangerous_attacks_away=data.get("dangerous_attacks_away", 0),
        xg_home=data.get("xg_home", 0.0),
        xg_away=data.get("xg_away", 0.0),
    )
