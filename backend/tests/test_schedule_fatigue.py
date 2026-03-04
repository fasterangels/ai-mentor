"""
Tests for schedule fatigue layer: days_since_last, matches_14, fatigue_score, deterministic.
Deterministic; use fixed 'now' in tests.
"""

from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

_backend = Path(__file__).resolve().parent.parent
_repo_root = _backend.parent
for _p in (_backend, _repo_root):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from backend.football.models import LastMatch
from backend.football.schedule_fatigue import (
    ScheduleFatigue,
    build_schedule_fatigue,
    compute_matches_last_14_days,
)


def _m(team_id: str, opponent: str, result: str, date_iso: str) -> LastMatch:
    return LastMatch(team_id=team_id, opponent=opponent, result=result, date_iso=date_iso)


# Fixed reference time for deterministic tests (UTC, timezone-aware)
_NOW = datetime(2026, 2, 15, 12, 0, 0, tzinfo=timezone.utc)


def test_days_since_last_match_non_negative() -> None:
    """days_since_last_match is always >= 0; empty matches returns 7."""
    empty = build_schedule_fatigue("T1", [], now=_NOW)
    assert empty.days_since_last_match == 7

    three_days_ago = (_NOW - timedelta(days=3)).strftime("%Y-%m-%dT12:00:00Z")
    matches = [_m("T1", "A", "W", three_days_ago)]
    result = build_schedule_fatigue("T1", matches, now=_NOW)
    assert result.days_since_last_match == 3
    assert result.days_since_last_match >= 0


def test_matches_last_14_days_counts_correctly() -> None:
    """matches_last_14_days counts matches with date_iso >= (now - 14 days)."""
    inside = (_NOW - timedelta(days=5)).strftime("%Y-%m-%dT12:00:00Z")
    outside = (_NOW - timedelta(days=20)).strftime("%Y-%m-%dT12:00:00Z")
    matches = [
        _m("T1", "A", "W", inside),
        _m("T1", "B", "L", outside),
    ]
    count = compute_matches_last_14_days(matches, now=_NOW)
    assert count == 1

    result = build_schedule_fatigue("T1", matches, now=_NOW)
    assert result.matches_last_14_days == 1


def test_fatigue_score_increases_with_more_matches_in_last_14_days() -> None:
    """More matches in last 14 days (with same rest) → higher fatigue_score."""
    base_date = (_NOW - timedelta(days=2)).strftime("%Y-%m-%dT12:00:00Z")
    few_matches = [_m("T1", "A", "W", base_date)]
    many_dates = [
        (_NOW - timedelta(days=d)).strftime("%Y-%m-%dT12:00:00Z")
        for d in (1, 3, 5, 7, 10)
    ]
    many_matches = [_m("T1", f"O{i}", "W", many_dates[i]) for i in range(5)]

    low = build_schedule_fatigue("T1", few_matches, now=_NOW)
    high = build_schedule_fatigue("T1", many_matches, now=_NOW)
    assert high.fatigue_score >= low.fatigue_score


def test_deterministic_output() -> None:
    """Same inputs and fixed now yield identical ScheduleFatigue."""
    date_iso = (_NOW - timedelta(days=1)).strftime("%Y-%m-%dT12:00:00Z")
    matches = [_m("T1", "A", "W", date_iso)]
    a = build_schedule_fatigue("T1", matches, now=_NOW)
    b = build_schedule_fatigue("T1", matches, now=_NOW)
    assert a.days_since_last_match == b.days_since_last_match
    assert a.matches_last_14_days == b.matches_last_14_days
    assert a.fatigue_score == b.fatigue_score
    assert a.rotation_risk == b.rotation_risk
