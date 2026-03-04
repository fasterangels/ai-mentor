"""
Unit tests for football feature builder v1 skeleton using mock providers.
"""

from __future__ import annotations

import sys
from pathlib import Path

_repo_root = Path(__file__).resolve().parents[2]
if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))

from backend.football.feature_builder import (  # type: ignore[import-error]
    build_features_payload,
)
from backend.football.mock_providers import (  # type: ignore[import-error]
    MockFootballOddsProvider,
    MockFootballStatsProvider,
)


def _build_payload() -> dict:
    stats = MockFootballStatsProvider()
    odds = MockFootballOddsProvider()
    return build_features_payload("MATCH_001", stats, odds)


def test_payload_has_required_keys() -> None:
    payload = _build_payload()
    for key in ["match", "lineups", "injuries", "last6", "h2h", "odds", "meta"]:
        assert key in payload


def test_last6_has_max_6_per_team() -> None:
    payload = _build_payload()
    last6 = payload["last6"]
    assert isinstance(last6, dict)
    for team_id, matches in last6.items():
        assert len(matches) <= 6
        # Each entry should be a dict with a result field.
        for m in matches:
            assert "result" in m


def test_odds_include_three_1x2_outcomes() -> None:
    payload = _build_payload()
    odds = payload["odds"]
    assert isinstance(odds, list)
    # Expect exactly three outcomes for 1x2 market.
    assert len(odds) == 3
    markets = {o["market"] for o in odds}
    assert markets == {"1x2"}
    outcomes = {o["outcome"] for o in odds}
    assert outcomes == {"home", "draw", "away"}


def test_build_features_payload_is_deterministic() -> None:
    stats = MockFootballStatsProvider()
    odds = MockFootballOddsProvider()
    p1 = build_features_payload("MATCH_DETERMINISTIC", stats, odds)
    p2 = build_features_payload("MATCH_DETERMINISTIC", stats, odds)
    for key in ["match", "lineups", "injuries", "last6", "h2h", "odds", "meta"]:
        assert key in p1
        assert key in p2
    assert p1["match"] == p2["match"]
    assert p1["lineups"] == p2["lineups"]
    assert p1["injuries"] == p2["injuries"]
    assert p1["last6"] == p2["last6"]
    assert p1["h2h"] == p2["h2h"]
    assert p1["odds"] == p2["odds"]
    assert "team_intelligence" in p1["meta"]
    assert "odds_intelligence" in p1["meta"]
    assert p1["meta"]["team_intelligence"] == p2["meta"]["team_intelligence"]
    assert p1["meta"]["odds_intelligence"] == p2["meta"]["odds_intelligence"]
    # market_movement may differ between calls (snapshot history)
    _ = p1["meta"].get("market_movement")
    _ = p2["meta"].get("market_movement")

