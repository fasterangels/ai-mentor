from __future__ import annotations

import sys
from pathlib import Path

import pytest

_backend = Path(__file__).resolve().parent.parent
if str(_backend) not in sys.path:
    sys.path.insert(0, str(_backend))

from pipeline.sources import get_registry  # noqa: E402
from pipeline.sources.head_to_head_source import HeadToHeadSource  # noqa: E402


def test_head_to_head_source_registers_for_both_kinds():
    reg = get_registry()
    h2h_sources = [s for s in reg.list_sources("head_to_head") if isinstance(s, HeadToHeadSource)]
    form_sources = [s for s in reg.list_sources("recent_form") if isinstance(s, HeadToHeadSource)]
    assert h2h_sources, "HeadToHeadSource should be registered for 'head_to_head'"
    assert form_sources, "HeadToHeadSource should be registered for 'recent_form'"
    src = h2h_sources[0]
    assert src.name == "head_to_head"
    assert src.priority == 35
    assert src.supports("head_to_head")
    assert src.supports("recent_form")


def test_head_to_head_empty_when_api_key_missing(monkeypatch):
    monkeypatch.delenv("FOOTBALL_DATA_API_KEY", raising=False)
    src = HeadToHeadSource()
    payload = src.fetch(
        "head_to_head",
        {"home_team": "Team A", "away_team": "Team B"},
    )
    h2h = payload["head_to_head"]
    assert h2h["matches"] == []
    assert h2h["summary"] == {
        "home_wins": 0,
        "away_wins": 0,
        "draws": 0,
        "avg_goals": 0.0,
    }
    assert payload["source_confidence"] == 0.0


def test_head_to_head_normalization(monkeypatch):
    """Head-to-head matches and summary are normalized correctly."""
    monkeypatch.setenv("FOOTBALL_DATA_API_KEY", "test-key")
    src = HeadToHeadSource()

    def fake_request(self, path, params, *, api_key: str):  # type: ignore[override]
        assert api_key == "test-key"
        assert path == "/matches"
        assert params["home"] == "Team A"
        assert params["away"] == "Team B"
        return {
            "matches": [
                {
                    "utcDate": "2024-01-01T18:00:00Z",
                    "homeTeam": {"name": "Team A"},
                    "awayTeam": {"name": "Team B"},
                    "score": {"fullTime": {"homeTeam": 2, "awayTeam": 1}},
                },
                {
                    "utcDate": "2024-02-01T18:00:00Z",
                    "homeTeam": {"name": "Team A"},
                    "awayTeam": {"name": "Team B"},
                    "score": {"fullTime": {"homeTeam": 0, "awayTeam": 0}},
                },
            ]
        }

    monkeypatch.setattr(
        "pipeline.sources.head_to_head_source.HeadToHeadSource._request",
        fake_request,
        raising=True,
    )

    payload = src.fetch(
        "head_to_head",
        {"home_team": "Team A", "away_team": "Team B"},
    )
    h2h = payload["head_to_head"]
    matches = h2h["matches"]
    summary = h2h["summary"]

    assert len(matches) == 2
    assert matches[0]["home_team"] == "Team A"
    assert matches[0]["away_team"] == "Team B"
    assert matches[0]["home_goals"] == 2
    assert matches[0]["away_goals"] == 1

    assert summary["home_wins"] == 1
    assert summary["away_wins"] == 0
    assert summary["draws"] == 1
    assert summary["avg_goals"] == pytest.approx((2 + 1 + 0 + 0) / 2.0)

