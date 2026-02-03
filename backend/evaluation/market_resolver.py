"""
Market outcome resolver: deterministic resolution of predicted picks vs final score.

Inputs: snapshot predicted picks (1X2, O/U2.5, GG/NG) and final score + status.
Outputs: per-market SUCCESS | FAILURE | NEUTRAL | UNRESOLVED.

Rules:
- NO_PREDICTION => outcome NEUTRAL.
- If match status != FINAL => all outcomes NEUTRAL (or UNRESOLVED; we use NEUTRAL for consistency).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

# Pick types (analyzer output)
PICK_1X2 = Literal["HOME", "DRAW", "AWAY", "NO_PREDICTION"]
PICK_OU = Literal["OVER", "UNDER", "NO_PREDICTION"]
PICK_GGNG = Literal["GG", "NG", "NO_PREDICTION"]

# Outcome types
OUTCOME_SUCCESS = "SUCCESS"
OUTCOME_FAILURE = "FAILURE"
OUTCOME_NEUTRAL = "NEUTRAL"
OUTCOME_UNRESOLVED = "UNRESOLVED"

# Match status
STATUS_FINAL = "FINAL"
STATUS_ABANDONED = "ABANDONED"
STATUS_POSTPONED = "POSTPONED"
STATUS_UNKNOWN = "UNKNOWN"


@dataclass
class SnapshotPicks:
    """Predicted picks for one snapshot (one per market)."""

    one_x_two: PICK_1X2  # HOME | DRAW | AWAY | NO_PREDICTION
    over_under_25: PICK_OU  # OVER | UNDER | NO_PREDICTION
    gg_ng: PICK_GGNG  # GG | NG | NO_PREDICTION


@dataclass
class FinalResult:
    """Final match result."""

    home_goals: int
    away_goals: int
    status: str  # FINAL | ABANDONED | POSTPONED | UNKNOWN


@dataclass
class MarketOutcomes:
    """Resolved outcome per market."""

    one_x_two: str  # SUCCESS | FAILURE | NEUTRAL | UNRESOLVED
    over_under_25: str
    gg_ng: str


def _result_1x2(home_goals: int, away_goals: int) -> Literal["HOME", "DRAW", "AWAY"]:
    """Compute 1X2 result from score."""
    if home_goals > away_goals:
        return "HOME"
    if home_goals < away_goals:
        return "AWAY"
    return "DRAW"


def _result_over_under_25(home_goals: int, away_goals: int) -> Literal["OVER", "UNDER"]:
    """O/U 2.5: OVER if total >= 3, UNDER if total <= 2."""
    total = home_goals + away_goals
    return "OVER" if total >= 3 else "UNDER"


def _result_gg_ng(home_goals: int, away_goals: int) -> Literal["GG", "NG"]:
    """GG if both teams scored, else NG."""
    if home_goals > 0 and away_goals > 0:
        return "GG"
    return "NG"


def resolve_markets(
    picks: SnapshotPicks,
    final: FinalResult,
) -> MarketOutcomes:
    """
    Resolve all three markets deterministically.

    - NO_PREDICTION => NEUTRAL.
    - status != FINAL => all outcomes NEUTRAL.
    - Otherwise: compare pick to computed result => SUCCESS or FAILURE.
    """
    if final.status != STATUS_FINAL:
        return MarketOutcomes(
            one_x_two=OUTCOME_NEUTRAL,
            over_under_25=OUTCOME_NEUTRAL,
            gg_ng=OUTCOME_NEUTRAL,
        )

    actual_1x2 = _result_1x2(final.home_goals, final.away_goals)
    actual_ou = _result_over_under_25(final.home_goals, final.away_goals)
    actual_ggng = _result_gg_ng(final.home_goals, final.away_goals)

    def _is_no_pick(pick: str) -> bool:
        return pick in ("NO_PREDICTION", "NO_BET")

    def _outcome_1x2() -> str:
        if _is_no_pick(picks.one_x_two):
            return OUTCOME_NEUTRAL
        return OUTCOME_SUCCESS if picks.one_x_two == actual_1x2 else OUTCOME_FAILURE

    def _outcome_ou() -> str:
        if _is_no_pick(picks.over_under_25):
            return OUTCOME_NEUTRAL
        return (
            OUTCOME_SUCCESS
            if picks.over_under_25 == actual_ou
            else OUTCOME_FAILURE
        )

    def _outcome_ggng() -> str:
        if _is_no_pick(picks.gg_ng):
            return OUTCOME_NEUTRAL
        return (
            OUTCOME_SUCCESS
            if picks.gg_ng == actual_ggng
            else OUTCOME_FAILURE
        )

    return MarketOutcomes(
        one_x_two=_outcome_1x2(),
        over_under_25=_outcome_ou(),
        gg_ng=_outcome_ggng(),
    )
