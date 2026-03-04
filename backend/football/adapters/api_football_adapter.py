"""
API-Football (api-sports.io) adapter: normalize fixtures/lineups/injuries to domain models.
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from ..models import (
    H2HItem,
    Injury,
    LastMatch,
    LineupPlayer,
    MatchRef,
    TeamRef,
)


def _parse_fixture(payload: Dict[str, Any]) -> MatchRef:
    """Parse API-Football fixtures response (single fixture) into MatchRef."""
    resp = payload.get("response") or []
    if not resp:
        raise ValueError("missing response")
    item = resp[0] if isinstance(resp, list) else resp
    if not isinstance(item, dict):
        raise ValueError("invalid fixture item")
    fixture = item.get("fixture") or {}
    league = item.get("league") or {}
    teams = item.get("teams") or {}
    home = teams.get("home") or {}
    away = teams.get("away") or {}
    try:
        match_id = str(fixture.get("id") or item.get("fixture", {}).get("id") or "")
        league_name = str(league.get("name") or "Unknown")
        date_str = str(fixture.get("date") or "")
        home_id = str(home.get("id") or "")
        home_name = str(home.get("name") or "Home")
        away_id = str(away.get("id") or "")
        away_name = str(away.get("name") or "Away")
    except (TypeError, AttributeError) as e:
        raise ValueError(f"fixture parse: {e}") from e
    return MatchRef(
        match_id=match_id,
        league=league_name,
        kickoff_iso=date_str,
        home=TeamRef(team_id=home_id, name=home_name),
        away=TeamRef(team_id=away_id, name=away_name),
    )


def _parse_lineups(payload: Dict[str, Any]) -> List[LineupPlayer]:
    """Parse API-Football lineups response into list of LineupPlayer."""
    out: List[LineupPlayer] = []
    resp = payload.get("response") or []
    if not isinstance(resp, list):
        return out
    for group in resp:
        if not isinstance(group, dict):
            continue
        team = group.get("team") or {}
        team_id = str(team.get("id") or "")
        for entry in group.get("startXI") or []:
            player_obj = (entry or {}).get("player") or {}
            name = str(player_obj.get("name") or "Unknown")
            out.append(LineupPlayer(team_id=team_id, player=name, role="starter"))
        for entry in group.get("substitutes") or []:
            player_obj = (entry or {}).get("player") or {}
            name = str(player_obj.get("name") or "Unknown")
            out.append(LineupPlayer(team_id=team_id, player=name, role="bench"))
    return out


def _parse_injuries(payload: Dict[str, Any]) -> List[Injury]:
    """Parse API-Football injuries response into list of Injury."""
    out: List[Injury] = []
    resp = payload.get("response") or []
    if not isinstance(resp, list):
        return out
    for item in resp:
        if not isinstance(item, dict):
            continue
        player_obj = item.get("player") or {}
        team_obj = item.get("team") or {}
        team_id = str(team_obj.get("id") or "")
        player_name = str(player_obj.get("name") or "Unknown")
        p = item.get("player") if isinstance(item.get("player"), dict) else {}
        inj_type = str(p.get("type") or item.get("type") or "injury")
        out.append(
            Injury(team_id=team_id, player=player_name, type=inj_type, status="out")
        )
    return out


def _goals_to_result(home_goals: int, away_goals: int, team_id: str, home_id: str, away_id: str) -> str:
    """Map fixture goals to W/D/L for the given team_id."""
    try:
        h = int(home_goals)
        a = int(away_goals)
    except (TypeError, ValueError):
        return "D"
    if team_id == str(home_id):
        return "W" if h > a else ("L" if h < a else "D")
    if team_id == str(away_id):
        return "W" if a > h else ("L" if a < h else "D")
    return "D"


def _parse_last_matches(payload: Dict[str, Any], team_id: str) -> List[LastMatch]:
    """Parse API-Football fixtures (team last N) into list of LastMatch. team_id is the team we asked for."""
    out: List[LastMatch] = []
    resp = payload.get("response") or []
    if not isinstance(resp, list):
        return out
    for item in resp[:6]:
        if not isinstance(item, dict):
            continue
        fixture = item.get("fixture") or {}
        teams = item.get("teams") or {}
        goals = item.get("goals") or {}
        home = teams.get("home") or {}
        away = teams.get("away") or {}
        home_id = home.get("id") or ""
        away_id = away.get("id") or ""
        opponent_name = (away.get("name") or "Away") if str(team_id) == str(home_id) else (home.get("name") or "Home")
        try:
            hg = int(goals.get("home", 0) or 0)
            ag = int(goals.get("away", 0) or 0)
        except (TypeError, ValueError):
            hg, ag = 0, 0
        result = _goals_to_result(hg, ag, team_id, home_id, away_id)
        date_iso = str(fixture.get("date") or "")
        out.append(
            LastMatch(
                team_id=team_id,
                opponent=str(opponent_name),
                result=result,
                date_iso=date_iso,
            )
        )
    return out[:6]


def _parse_h2h(payload: Dict[str, Any]) -> List[H2HItem]:
    """Parse API-Football headtohead fixtures into list of H2HItem."""
    out: List[H2HItem] = []
    resp = payload.get("response") or []
    if not isinstance(resp, list):
        return out
    for item in resp[:6]:
        if not isinstance(item, dict):
            continue
        fixture = item.get("fixture") or {}
        goals = item.get("goals") or {}
        try:
            home_goals = int(goals.get("home", 0) or 0)
            away_goals = int(goals.get("away", 0) or 0)
        except (TypeError, ValueError):
            home_goals, away_goals = 0, 0
        date_iso = str(fixture.get("date") or "")
        out.append(H2HItem(home_goals=home_goals, away_goals=away_goals, date_iso=date_iso))
    return out[:6]


class ApiFootballStatsProvider:
    """
    Stats provider using API-Football (api-sports.io). Enabled when API_FOOTBALL_KEY is set.
    """

    name: str = "api_football"

    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
        timeout: int = 10,
    ) -> None:
        self.base_url = (base_url or os.environ.get("API_FOOTBALL_BASE_URL") or "https://v3.football.api-sports.io").rstrip("/")
        self.api_key = api_key or os.environ.get("API_FOOTBALL_KEY") or ""
        self.timeout = timeout

    def _request(self, path: str, params: Dict[str, Any]) -> Dict[str, Any]:
        if not self.api_key:
            return {}
        url = f"{self.base_url}/{path.lstrip('/')}?{urlencode(params)}"
        headers = {"x-rapidapi-key": self.api_key, "x-apisports-key": self.api_key, "User-Agent": "ai-mentor-api-football"}
        req = Request(url, headers=headers)
        with urlopen(req, timeout=self.timeout) as resp:  # type: ignore[arg-type]
            raw = resp.read()
        return json.loads(raw.decode("utf-8"))

    def get_match(self, match_id: str) -> MatchRef:
        data = self._request("fixtures", {"id": match_id})
        if not data or not data.get("response"):
            raise ValueError("api_football: no fixture response")
        try:
            return _parse_fixture(data)
        except (ValueError, KeyError, TypeError) as e:
            raise ValueError(f"api_football: get_match parse failed ({e})") from e

    def get_lineups(self, match_id: str) -> List[LineupPlayer]:
        data = self._request("fixtures/lineups", {"fixture": match_id})
        if not data:
            return []
        try:
            return _parse_lineups(data)
        except Exception:
            return []

    def get_injuries(self, match_id: str) -> List[Injury]:
        data = self._request("injuries", {"fixture": match_id})
        if not data:
            return []
        try:
            return _parse_injuries(data)
        except Exception:
            return []

    def get_last_matches(self, team_id: str, n: int = 6) -> List[LastMatch]:
        data = self._request("fixtures", {"team": team_id, "last": n})
        if not data:
            return []
        try:
            return _parse_last_matches(data, team_id)[:n]
        except Exception:
            return []

    def get_h2h(self, home_team_id: str, away_team_id: str, n: int = 6) -> List[H2HItem]:
        h2h_param = f"{home_team_id}-{away_team_id}"
        data = self._request("fixtures/headtohead", {"h2h": h2h_param, "last": n})
        if not data:
            return []
        try:
            return _parse_h2h(data)[:n]
        except Exception:
            return []
