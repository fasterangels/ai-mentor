from __future__ import annotations

from dataclasses import dataclass, is_dataclass, asdict
from typing import Any, Dict, List


@dataclass
class TeamRef:
    team_id: str
    name: str


@dataclass
class MatchRef:
    match_id: str
    league: str
    kickoff_iso: str
    home: TeamRef
    away: TeamRef


@dataclass
class Injury:
    team_id: str
    player: str
    type: str  # e.g. "injury" / "suspension"
    status: str  # e.g. "out"


@dataclass
class LineupPlayer:
    team_id: str
    player: str
    role: str  # "starter" / "bench"


@dataclass
class LastMatch:
    team_id: str
    opponent: str
    result: str  # "W" / "D" / "L"
    date_iso: str


@dataclass
class H2HItem:
    home_goals: int
    away_goals: int
    date_iso: str


@dataclass
class OddsQuote:
    bookmaker: str
    market: str  # e.g. "1x2"
    outcome: str  # e.g. "home" / "draw" / "away"
    price: float


@dataclass
class FootballFeatures:
    match: MatchRef
    lineups: List[LineupPlayer]
    injuries: List[Injury]
    last6: Dict[str, List[LastMatch]]  # team_id -> list (max 6)
    h2h: List[H2HItem]
    odds: List[OddsQuote]
    meta: Dict[str, Any]


def asdict_deep(obj: Any) -> Any:
    """
    Deterministic deep conversion of dataclasses and containers into plain dicts/lists.

    - Dataclasses are converted via asdict, then keys are sorted recursively.
    - Dict keys are always emitted in sorted order.
    - Lists and tuples preserve element order.
    """
    if is_dataclass(obj):
        obj = asdict(obj)

    if isinstance(obj, dict):
        return {key: asdict_deep(obj[key]) for key in sorted(obj.keys())}
    if isinstance(obj, list):
        return [asdict_deep(v) for v in obj]
    if isinstance(obj, tuple):
        return [asdict_deep(v) for v in obj]
    return obj

