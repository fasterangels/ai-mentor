"""Unit tests for market resolver — deterministic outcome resolution."""

from __future__ import annotations

import sys
from pathlib import Path

_backend = Path(__file__).resolve().parent.parent
if str(_backend) not in sys.path:
    sys.path.insert(0, str(_backend))

from evaluation.market_resolver import (
    FinalResult,
    MarketOutcomes,
    SnapshotPicks,
    resolve_markets,
    OUTCOME_FAILURE,
    OUTCOME_NEUTRAL,
    OUTCOME_SUCCESS,
    STATUS_ABANDONED,
    STATUS_FINAL,
    STATUS_POSTPONED,
)


def test_resolve_1x2_home_win():
    """1X2: pick HOME, result 2-1 => SUCCESS."""
    picks = SnapshotPicks(one_x_two="HOME", over_under_25="OVER", gg_ng="GG")
    final = FinalResult(home_goals=2, away_goals=1, status=STATUS_FINAL)
    out = resolve_markets(picks, final)
    assert out.one_x_two == OUTCOME_SUCCESS
    assert out.over_under_25 == OUTCOME_SUCCESS  # 3 goals = OVER
    assert out.gg_ng == OUTCOME_SUCCESS  # both scored


def test_resolve_1x2_draw():
    """1X2: pick DRAW, result 1-1 => SUCCESS."""
    picks = SnapshotPicks(one_x_two="DRAW", over_under_25="UNDER", gg_ng="GG")
    final = FinalResult(home_goals=1, away_goals=1, status=STATUS_FINAL)
    out = resolve_markets(picks, final)
    assert out.one_x_two == OUTCOME_SUCCESS
    assert out.over_under_25 == OUTCOME_SUCCESS  # 2 goals = UNDER
    assert out.gg_ng == OUTCOME_SUCCESS


def test_resolve_1x2_away_win_failure():
    """1X2: pick HOME, result 0-1 => FAILURE."""
    picks = SnapshotPicks(one_x_two="HOME", over_under_25="NO_PREDICTION", gg_ng="NO_PREDICTION")
    final = FinalResult(home_goals=0, away_goals=1, status=STATUS_FINAL)
    out = resolve_markets(picks, final)
    assert out.one_x_two == OUTCOME_FAILURE
    assert out.over_under_25 == OUTCOME_NEUTRAL
    assert out.gg_ng == OUTCOME_NEUTRAL


def test_no_prediction_neutral():
    """NO_PREDICTION => NEUTRAL for that market."""
    picks = SnapshotPicks(one_x_two="NO_PREDICTION", over_under_25="NO_PREDICTION", gg_ng="NO_PREDICTION")
    final = FinalResult(home_goals=2, away_goals=1, status=STATUS_FINAL)
    out = resolve_markets(picks, final)
    assert out.one_x_two == OUTCOME_NEUTRAL
    assert out.over_under_25 == OUTCOME_NEUTRAL
    assert out.gg_ng == OUTCOME_NEUTRAL


def test_no_bet_neutral():
    """NO_BET => NEUTRAL (treated like NO_PREDICTION)."""
    picks = SnapshotPicks(one_x_two="NO_BET", over_under_25="NO_BET", gg_ng="NO_BET")
    final = FinalResult(home_goals=2, away_goals=1, status=STATUS_FINAL)
    out = resolve_markets(picks, final)
    assert out.one_x_two == OUTCOME_NEUTRAL
    assert out.over_under_25 == OUTCOME_NEUTRAL
    assert out.gg_ng == OUTCOME_NEUTRAL


def test_non_final_status_all_neutral():
    """If status != FINAL => all outcomes NEUTRAL."""
    picks = SnapshotPicks(one_x_two="HOME", over_under_25="OVER", gg_ng="GG")
    for status in (STATUS_ABANDONED, STATUS_POSTPONED, "UNKNOWN"):
        final = FinalResult(home_goals=2, away_goals=1, status=status)
        out = resolve_markets(picks, final)
        assert out.one_x_two == OUTCOME_NEUTRAL
        assert out.over_under_25 == OUTCOME_NEUTRAL
        assert out.gg_ng == OUTCOME_NEUTRAL


def test_ou25_over_under():
    """O/U 2.5: total >= 3 => OVER, total <= 2 => UNDER."""
    final_over = FinalResult(home_goals=2, away_goals=1, status=STATUS_FINAL)
    final_under = FinalResult(home_goals=1, away_goals=1, status=STATUS_FINAL)
    picks_over = SnapshotPicks(one_x_two="NO_PREDICTION", over_under_25="OVER", gg_ng="NO_PREDICTION")
    picks_under = SnapshotPicks(one_x_two="NO_PREDICTION", over_under_25="UNDER", gg_ng="NO_PREDICTION")
    out_over = resolve_markets(picks_over, final_over)
    out_under = resolve_markets(picks_under, final_under)
    assert out_over.over_under_25 == OUTCOME_SUCCESS
    assert out_under.over_under_25 == OUTCOME_SUCCESS


def test_ou25_boundary_2_goals_under():
    """Total 2 => UNDER."""
    picks = SnapshotPicks(one_x_two="NO_PREDICTION", over_under_25="UNDER", gg_ng="NO_PREDICTION")
    final = FinalResult(home_goals=1, away_goals=1, status=STATUS_FINAL)
    out = resolve_markets(picks, final)
    assert out.over_under_25 == OUTCOME_SUCCESS


def test_ou25_boundary_3_goals_over():
    """Total 3 => OVER."""
    picks = SnapshotPicks(one_x_two="NO_PREDICTION", over_under_25="OVER", gg_ng="NO_PREDICTION")
    final = FinalResult(home_goals=2, away_goals=1, status=STATUS_FINAL)
    out = resolve_markets(picks, final)
    assert out.over_under_25 == OUTCOME_SUCCESS


def test_gg_ng():
    """GG = both scored, NG = otherwise."""
    picks_gg = SnapshotPicks(one_x_two="NO_PREDICTION", over_under_25="NO_PREDICTION", gg_ng="GG")
    picks_ng = SnapshotPicks(one_x_two="NO_PREDICTION", over_under_25="NO_PREDICTION", gg_ng="NG")
    final_both = FinalResult(home_goals=1, away_goals=1, status=STATUS_FINAL)
    final_ng = FinalResult(home_goals=2, away_goals=0, status=STATUS_FINAL)
    assert resolve_markets(picks_gg, final_both).gg_ng == OUTCOME_SUCCESS
    assert resolve_markets(picks_ng, final_both).gg_ng == OUTCOME_FAILURE
    assert resolve_markets(picks_ng, final_ng).gg_ng == OUTCOME_SUCCESS
    assert resolve_markets(picks_gg, final_ng).gg_ng == OUTCOME_FAILURE
