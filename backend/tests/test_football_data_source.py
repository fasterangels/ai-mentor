from __future__ import annotations

import sys
from pathlib import Path

import pytest

_backend = Path(__file__).resolve().parent.parent
if str(_backend) not in sys.path:
    sys.path.insert(0, str(_backend))

from pipeline.sources import get_registry  # noqa: E402
from pipeline.sources.football_data_api import FootballDataAPISource  # noqa: E402


def test_football_data_source_registers_and_supports_fixtures():
    reg = get_registry()
    sources = reg.list_sources('fixtures')
    fd_sources = [s for s in sources if isinstance(s, FootballDataAPISource)]
    assert fd_sources, 'FootballDataAPISource should be registered in the default registry'
    src = fd_sources[0]
    assert src.supports('fixtures')
    assert src.supports('recent_matches')
    assert src.name == 'football_data_api'
    assert src.priority == 50


def test_football_data_source_missing_api_key_returns_empty(monkeypatch):
    monkeypatch.delenv('FOOTBALL_DATA_API_KEY', raising=False)
    src = FootballDataAPISource()
    payload = src.fetch(
        'fixtures',
        {'team_home': 'Team A', 'team_away': 'Team B', 'date': '2026-02-01'},
    )
    # Empty but well-formed payload with matches list present.
    assert 'matches' in payload
    assert payload['matches'] == []
    assert 'data' in payload
    assert payload['data'] == {'matches': []}


def test_football_data_source_uses_http_and_normalizes(monkeypatch):
    monkeypatch.setenv('FOOTBALL_DATA_API_KEY', 'test-key')
    src = FootballDataAPISource()

    def fake_request(self, path, params, *, api_key: str):  # type: ignore[override]
        assert path == '/matches'
        assert api_key == 'test-key'
        # Echo back params for basic sanity.
        assert 'dateFrom' in params and 'dateTo' in params
        return {
            'matches': [
                {
                    'id': 123,
                    'utcDate': '2026-02-01T18:00:00Z',
                    'status': 'SCHEDULED',
                    'competition': {'name': 'Test League'},
                    'homeTeam': {'name': 'Team A'},
                    'awayTeam': {'name': 'Team B'},
                },
                {
                    # Different pairing: should be filtered out
                    'id': 456,
                    'utcDate': '2026-02-01T18:00:00Z',
                    'status': 'SCHEDULED',
                    'competition': {'name': 'Other League'},
                    'homeTeam': {'name': 'Other Home'},
                    'awayTeam': {'name': 'Other Away'},
                },
            ]
        }

    monkeypatch.setattr(
        'pipeline.sources.football_data_api.FootballDataAPISource._request',
        fake_request,
        raising=True,
    )

    payload = src.fetch(
        'fixtures',
        {'team_home': 'Team A', 'team_away': 'Team B', 'date': '2026-02-01'},
    )
    matches = payload.get('matches') or []
    assert len(matches) == 1
    m = matches[0]
    assert m['home_team'] == 'team a'
    assert m['away_team'] == 'team b'
    assert m['competition'] == 'Test League'
    assert m['status'] == 'SCHEDULED'
