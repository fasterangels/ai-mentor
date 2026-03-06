"""
HTTP JSON football providers (stdlib urllib). Expect APIs returning normalized schema.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .models import (
    H2HItem,
    Injury,
    LastMatch,
    LineupPlayer,
    MatchRef,
    OddsQuote,
    TeamRef,
)


def _parse_team_ref(d: Dict[str, Any]) -> TeamRef:
    return TeamRef(team_id=str(d["team_id"]), name=str(d["name"]))


def _parse_match_ref(d: Dict[str, Any]) -> MatchRef:
    return MatchRef(
        match_id=str(d["match_id"]),
        league=str(d["league"]),
        kickoff_iso=str(d["kickoff_iso"]),
        home=_parse_team_ref(d["home"]),
        away=_parse_team_ref(d["away"]),
    )


def _parse_lineup_player(d: Dict[str, Any]) -> LineupPlayer:
    return LineupPlayer(
        team_id=str(d["team_id"]),
        player=str(d["player"]),
        role=str(d["role"]),
    )


def _parse_injury(d: Dict[str, Any]) -> Injury:
    return Injury(
        team_id=str(d["team_id"]),
        player=str(d["player"]),
        type=str(d["type"]),
        status=str(d["status"]),
    )


def _parse_last_match(d: Dict[str, Any]) -> LastMatch:
    return LastMatch(
        team_id=str(d["team_id"]),
        opponent=str(d["opponent"]),
        result=str(d["result"]),
        date_iso=str(d["date_iso"]),
    )


def _parse_h2h_item(d: Dict[str, Any]) -> H2HItem:
    return H2HItem(
        home_goals=int(d["home_goals"]),
        away_goals=int(d["away_goals"]),
        date_iso=str(d["date_iso"]),
    )


def _parse_odds_quote(d: Dict[str, Any]) -> OddsQuote:
    return OddsQuote(
        bookmaker=str(d["bookmaker"]),
        market=str(d["market"]),
        outcome=str(d["outcome"]),
        price=float(d["price"]),
    )


class HttpJsonFootballStatsProvider:
    """
    Football stats provider that calls a JSON HTTP API (normalized schema).
    """

    name: str = "http_stats"

    def __init__(
        self,
        base_url: str,
        api_key: str | None = None,
        timeout: int = 10,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout

    def _request(self, path: str, params: Dict[str, Any]) -> Dict[str, Any]:
        url = f"{self.base_url}{path}?{urlencode(params)}"
        headers: Dict[str, str] = {"User-Agent": "ai-mentor-football-http"}
        if self.api_key:
            headers["X-API-KEY"] = self.api_key
        req = Request(url, headers=headers)
        with urlopen(req, timeout=self.timeout) as resp:  # type: ignore[arg-type]
            raw = resp.read()
        return json.loads(raw.decode("utf-8"))

    def get_match(self, match_id: str) -> MatchRef:
        data = self._request("/match", {"match_id": match_id})
        return _parse_match_ref(data)

    def get_lineups(self, match_id: str) -> List[LineupPlayer]:
        data = self._request("/lineups", {"match_id": match_id})
        if isinstance(data, list):
            return [_parse_lineup_player(item) for item in data]
        return [_parse_lineup_player(item) for item in data.get("lineups", [])]

    def get_injuries(self, match_id: str) -> List[Injury]:
        data = self._request("/injuries", {"match_id": match_id})
        if isinstance(data, list):
            return [_parse_injury(item) for item in data]
        return [_parse_injury(item) for item in data.get("injuries", [])]

    def get_last_matches(self, team_id: str, n: int = 6) -> List[LastMatch]:
        data = self._request("/last_matches", {"team_id": team_id, "n": n})
        if isinstance(data, list):
            return [_parse_last_match(item) for item in data]
        lst = data.get("last_matches", data.get("last6", []))
        return [_parse_last_match(item) for item in lst]

    def get_h2h(
        self,
        home_team_id: str,
        away_team_id: str,
        n: int = 6,
    ) -> List[H2HItem]:
        data = self._request(
            "/h2h",
            {
                "home_team_id": home_team_id,
                "away_team_id": away_team_id,
                "n": n,
            },
        )
        if isinstance(data, list):
            return [_parse_h2h_item(item) for item in data]
        return [_parse_h2h_item(item) for item in data.get("h2h", [])]


class HttpJsonFootballOddsProvider:
    """
    Football odds provider that calls a JSON HTTP API.
    """

    name: str = "http_odds"

    def __init__(
        self,
        base_url: str,
        api_key: str | None = None,
        timeout: int = 10,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout

    def _request(self, path: str, params: Dict[str, Any]) -> Dict[str, Any]:
        url = f"{self.base_url}{path}?{urlencode(params)}"
        headers: Dict[str, str] = {"User-Agent": "ai-mentor-football-http"}
        if self.api_key:
            headers["X-API-KEY"] = self.api_key
        req = Request(url, headers=headers)
        with urlopen(req, timeout=self.timeout) as resp:  # type: ignore[arg-type]
            raw = resp.read()
        return json.loads(raw.decode("utf-8"))

    def get_odds(self, match_id: str) -> List[OddsQuote]:
        data = self._request("/odds", {"match_id": match_id})
        odds = data.get("odds", []) if isinstance(data, dict) else []
        return [_parse_odds_quote(item) for item in odds]
