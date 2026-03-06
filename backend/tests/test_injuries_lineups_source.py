from __future__ import annotations

import sys
from pathlib import Path

import pytest

_backend = Path(__file__).resolve().parent.parent
if str(_backend) not in sys.path:
    sys.path.insert(0, str(_backend))

from pipeline.sources import get_registry  # noqa: E402
from pipeline.sources.injuries_lineups_source import InjuriesLineupsSource  # noqa: E402


def test_injuries_lineups_source_registers_for_both_kinds():
    reg = get_registry()
    injuries_sources = [s for s in reg.list_sources("injuries") if isinstance(s, InjuriesLineupsSource)]
    lineups_sources = [s for s in reg.list_sources("lineups") if isinstance(s, InjuriesLineupsSource)]
    assert injuries_sources, "InjuriesLineupsSource should be registered for 'injuries'"
    assert lineups_sources, "InjuriesLineupsSource should be registered for 'lineups'"
    src = injuries_sources[0]
    assert src.name == "injuries_lineups"
    assert src.priority == 45
    assert src.supports("injuries")
    assert src.supports("lineups")


def test_injuries_empty_payload_when_api_key_missing(monkeypatch):
    monkeypatch.delenv("FOOTBALL_DATA_API_KEY", raising=False)
    src = InjuriesLineupsSource()
    payload = src.fetch(
        "injuries",
        {"home_team": "Team A", "away_team": "Team B"},
    )
    assert payload["injuries"] == []
    assert payload["data"] == {"injuries": []}
    assert payload["source_confidence"] == 0.0


def test_injuries_normalization(monkeypatch):
    """Injuries payload is normalized to expected shape and status buckets."""
    monkeypatch.setenv("FOOTBALL_DATA_API_KEY", "test-key")
    src = InjuriesLineupsSource()

    def fake_request(self, path, params, *, api_key: str):  # type: ignore[override]
        assert api_key == "test-key"
        assert path == "/injuries"
        assert params["home"] == "Team A"
        assert params["away"] == "Team B"
        return {
            "injuries": [
                {
                    "team": "Team A",
                    "player": "Player 1",
                    "position": "FW",
                    "reason": "Knee injury",
                    "status": "Injury",
                },
                {
                    "team": "Team B",
                    "name": "Player 2",
                    "position": "DF",
                    "description": "Red card ban",
                    "status": "Suspended",
                },
                {
                    "team": "Team A",
                    "player": "Player 3",
                    "position": "MF",
                    "reason": "Minor knock",
                    "status": "Doubtful",
                },
            ]
        }

    monkeypatch.setattr(
        "pipeline.sources.injuries_lineups_source.InjuriesLineupsSource._request",
        fake_request,
        raising=True,
    )

    payload = src.fetch(
        "injuries",
        {"home_team": "Team A", "away_team": "Team B"},
    )
    injuries = payload["injuries"]
    assert len(injuries) == 3

    a1 = injuries[0]
    assert a1["team"] == "Team A"
    assert a1["player"] == "Player 1"
    assert a1["position"] == "FW"
    assert a1["reason"] == "Knee injury"
    assert a1["status"] == "injured"

    b = injuries[1]
    assert b["team"] == "Team B"
    assert b["player"] == "Player 2"
    assert b["position"] == "DF"
    assert b["reason"] == "Red card ban"
    assert b["status"] == "suspended"

    a2 = injuries[2]
    assert a2["team"] == "Team A"
    assert a2["player"] == "Player 3"
    assert a2["position"] == "MF"
    assert a2["reason"] == "Minor knock"
    assert a2["status"] == "doubtful"

