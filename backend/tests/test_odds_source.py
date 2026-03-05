from __future__ import annotations

import sys
from pathlib import Path

import pytest

_backend = Path(__file__).resolve().parent.parent
if str(_backend) not in sys.path:
    sys.path.insert(0, str(_backend))

from pipeline.sources import get_registry  # noqa: E402
from pipeline.sources.odds_api_source import OddsAPISource  # noqa: E402


def test_odds_source_registers_for_odds_kind():
    reg = get_registry()
    sources = reg.list_sources("odds")
    odds_sources = [s for s in sources if isinstance(s, OddsAPISource)]
    assert odds_sources, "OddsAPISource should be registered in the default registry"
    src = odds_sources[0]
    assert src.supports("odds")
    assert src.name == "odds_api"
    assert src.priority == 40


def test_odds_source_missing_api_key_returns_empty(monkeypatch):
    monkeypatch.delenv("ODDS_API_KEY", raising=False)
    src = OddsAPISource()
    payload = src.fetch(
        "odds",
        {"home_team": "Team A", "away_team": "Team B", "date": "2026-02-01"},
    )
    assert "odds" in payload
    assert payload["odds"] == {}
    assert payload["data"] == {"odds": {}}
    assert payload["source_confidence"] == 0.0


def test_odds_source_normalizes_best_and_average(monkeypatch):
    monkeypatch.setenv("ODDS_API_KEY", "test-key")
    src = OddsAPISource()

    def fake_request(self, params):  # type: ignore[override]
        assert params["apiKey"] == "test-key"
        # Single event matching our home/away/date
        return [
            {
                "home_team": "Team A",
                "away_team": "Team B",
                "commence_time": "2026-02-01T18:00:00Z",
                "bookmakers": [
                    {
                        "markets": [
                            {
                                "key": "h2h",
                                "outcomes": [
                                    {"name": "Team A", "price": 2.0},
                                    {"name": "Draw", "price": 3.4},
                                    {"name": "Team B", "price": 4.0},
                                ],
                            },
                            {
                                "key": "totals",
                                "outcomes": [
                                    {"name": "Over 2.5", "point": 2.5, "price": 1.9},
                                    {"name": "Under 2.5", "point": 2.5, "price": 1.9},
                                ],
                            },
                            {
                                "key": "btts",
                                "outcomes": [
                                    {"name": "Yes", "price": 1.7},
                                    {"name": "No", "price": 2.2},
                                ],
                            },
                        ]
                    },
                    {
                        "markets": [
                            {
                                "key": "h2h",
                                "outcomes": [
                                    {"name": "Team A", "price": 2.2},
                                    {"name": "Draw", "price": 3.6},
                                    {"name": "Team B", "price": 3.8},
                                ],
                            },
                            {
                                "key": "totals",
                                "outcomes": [
                                    {"name": "Over 2.5", "point": 2.5, "price": 2.0},
                                    {"name": "Under 2.5", "point": 2.5, "price": 1.8},
                                ],
                            },
                            {
                                "key": "btts",
                                "outcomes": [
                                    {"name": "Yes", "price": 1.6},
                                    {"name": "No", "price": 2.4},
                                ],
                            },
                        ]
                    },
                ],
            }
        ]

    monkeypatch.setattr(
        "pipeline.sources.odds_api_source.OddsAPISource._request",
        fake_request,
        raising=True,
    )

    payload = src.fetch(
        "odds",
        {"home_team": "Team A", "away_team": "Team B", "date": "2026-02-01"},
    )
    odds = payload["odds"]

    one_x_two = odds["1x2"]
    # Home: prices 2.0 and 2.2 -> best 2.2, avg 2.1
    assert one_x_two["home"]["best"] == pytest.approx(2.2)
    assert one_x_two["home"]["avg"] == pytest.approx(2.1)
    # Draw: 3.4 and 3.6 -> best 3.6, avg 3.5
    assert one_x_two["draw"]["best"] == pytest.approx(3.6)
    assert one_x_two["draw"]["avg"] == pytest.approx(3.5)
    # Away: 4.0 and 3.8 -> best 4.0, avg 3.9
    assert one_x_two["away"]["best"] == pytest.approx(4.0)
    assert one_x_two["away"]["avg"] == pytest.approx(3.9)

    ou = odds["over_under_2_5"]
    # Over: 1.9 and 2.0 -> best 2.0, avg 1.95
    assert ou["over"]["best"] == pytest.approx(2.0)
    assert ou["over"]["avg"] == pytest.approx(1.95)
    # Under: 1.9 and 1.8 -> best 1.9, avg 1.85
    assert ou["under"]["best"] == pytest.approx(1.9)
    assert ou["under"]["avg"] == pytest.approx(1.85)

    btts = odds["btts"]
    # Yes: 1.7 and 1.6 -> best 1.7, avg 1.65
    assert btts["yes"]["best"] == pytest.approx(1.7)
    assert btts["yes"]["avg"] == pytest.approx(1.65)
    # No: 2.2 and 2.4 -> best 2.4, avg 2.3
    assert btts["no"]["best"] == pytest.approx(2.4)
    assert btts["no"]["avg"] == pytest.approx(2.3)

