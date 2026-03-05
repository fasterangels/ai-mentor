from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, List
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .base import Source

_BASE_URL = "https://api.football-data.org/v4"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class HeadToHeadSource(Source):
    """Head-to-head matchups and recent form via football-data.org (v1 simple integration)."""

    _PRIORITY = 35

    @property
    def name(self) -> str:
        return "head_to_head"

    @property
    def priority(self) -> int:
        return self._PRIORITY

    def supports(self, kind: str) -> bool:
        return kind in ("head_to_head", "recent_form")

    def fetch(self, kind: str, query: Dict[str, Any]) -> Dict[str, Any]:
        """Fetch head-to-head or recent form with fail-safe behaviour.

        - Missing API key -> empty structure
        - Network/HTTP/JSON errors -> empty structure
        - Missing required query fields -> empty structure
        """
        api_key = os.getenv("FOOTBALL_DATA_API_KEY") or ""
        if not api_key:
            return self._empty_payload(kind)

        try:
            if kind == "head_to_head":
                return self._fetch_head_to_head(query, api_key)
            if kind == "recent_form":
                return self._fetch_recent_form(query, api_key)
        except (HTTPError, URLError, TimeoutError, ValueError, json.JSONDecodeError):
            return self._empty_payload(kind)

        return self._empty_payload(kind)

    # ------------------------------------------------------------------ helpers

    def _empty_payload(self, kind: str) -> Dict[str, Any]:
        if kind == "head_to_head":
            data: Dict[str, Any] = {
                "head_to_head": {
                    "matches": [],
                    "summary": {
                        "home_wins": 0,
                        "away_wins": 0,
                        "draws": 0,
                        "avg_goals": 0.0,
                    },
                }
            }
        elif kind == "recent_form":
            data = {"recent_form": []}
        else:
            data = {}
        payload: Dict[str, Any] = {
            "data": data,
            "fetched_at_utc": _now_iso(),
            "source_confidence": 0.0,
        }
        payload.update(data)
        return payload

    def _request(self, path: str, params: Dict[str, Any], *, api_key: str) -> Dict[str, Any]:
        """Low-level GET; tests mock this method so exact endpoint is abstracted."""
        qs = urlencode(params)
        url = f"{_BASE_URL}{path}"
        if qs:
            url = f"{url}?{qs}"
        req = Request(url)
        req.add_header("X-Auth-Token", api_key)
        req.add_header("Accept", "application/json")
        with urlopen(req, timeout=10) as resp:
            charset = resp.headers.get_content_charset() or "utf-8"
            body = resp.read().decode(charset)
            data = json.loads(body)
        if isinstance(data, dict):
            return data
        return {}

    # ----------------------------- head_to_head: historical matches and summary

    def _fetch_head_to_head(self, query: Dict[str, Any], api_key: str) -> Dict[str, Any]:
        home_team = (query.get("home_team") or "").strip()
        away_team = (query.get("away_team") or "").strip()
        if not (home_team and away_team):
            return self._empty_payload("head_to_head")

        raw = self._request(
            "/matches",
            {"home": home_team, "away": away_team},
            api_key=api_key,
        )
        matches_raw = raw.get("matches") or []
        if not isinstance(matches_raw, list):
            matches_raw = []

        matches: List[Dict[str, Any]] = []
        home_wins = away_wins = draws = 0
        total_goals = 0.0
        games = 0

        for m in matches_raw:
            if not isinstance(m, Dict):
                continue
            home_name = (m.get("homeTeam", {}) or {}).get("name") or ""
            away_name = (m.get("awayTeam", {}) or {}).get("name") or ""
            # Only consider fixtures matching the given home/away roles
            if home_name.strip() != home_team or away_name.strip() != away_team:
                continue
            score = (m.get("score", {}) or {}).get("fullTime", {}) or {}
            hg = score.get("homeTeam")
            ag = score.get("awayTeam")
            try:
                hg_int = int(hg)
                ag_int = int(ag)
            except (TypeError, ValueError):
                continue

            matches.append(
                {
                    "date": m.get("utcDate"),
                    "home_team": home_name,
                    "away_team": away_name,
                    "home_goals": hg_int,
                    "away_goals": ag_int,
                }
            )

            games += 1
            total_goals += hg_int + ag_int
            if hg_int > ag_int:
                home_wins += 1
            elif ag_int > hg_int:
                away_wins += 1
            else:
                draws += 1

        avg_goals = (total_goals / games) if games else 0.0
        summary = {
            "home_wins": home_wins,
            "away_wins": away_wins,
            "draws": draws,
            "avg_goals": avg_goals,
        }
        head_to_head = {"matches": matches, "summary": summary}
        data: Dict[str, Any] = {"head_to_head": head_to_head}
        payload: Dict[str, Any] = {
            "data": data,
            "head_to_head": data["head_to_head"],
            "fetched_at_utc": _now_iso(),
            "source_confidence": 0.9 if matches else 0.5,
        }
        return payload

    # ----------------------------- recent_form: last matches for a team

    def _fetch_recent_form(self, query: Dict[str, Any], api_key: str) -> Dict[str, Any]:
        team = (query.get("team") or "").strip()
        if not team:
            return self._empty_payload("recent_form")

        raw = self._request(
            "/recent_form",
            {"team": team},
            api_key=api_key,
        )
        matches_raw = raw.get("matches") or raw.get("recent") or []
        if not isinstance(matches_raw, list):
            matches_raw = []

        recent: List[Dict[str, Any]] = []
        t_lower = team.lower()

        for m in matches_raw:
            if not isinstance(m, Dict):
                continue
            home_name = (m.get("homeTeam", {}) or {}).get("name") or ""
            away_name = (m.get("awayTeam", {}) or {}).get("name") or ""
            score = (m.get("score", {}) or {}).get("fullTime", {}) or {}
            hg = score.get("homeTeam")
            ag = score.get("awayTeam")
            try:
                hg_int = int(hg)
                ag_int = int(ag)
            except (TypeError, ValueError):
                continue

            side = None
            opponent = ""
            if home_name.lower() == t_lower:
                side = "home"
                opponent = away_name
                goals_for, goals_against = hg_int, ag_int
            elif away_name.lower() == t_lower:
                side = "away"
                opponent = home_name
                goals_for, goals_against = ag_int, hg_int
            else:
                continue

            if goals_for > goals_against:
                result = "W"
            elif goals_for < goals_against:
                result = "L"
            else:
                result = "D"

            recent.append(
                {
                    "date": m.get("utcDate"),
                    "opponent": opponent,
                    "goals_for": goals_for,
                    "goals_against": goals_against,
                    "result": result,
                }
            )

        data: Dict[str, Any] = {"recent_form": recent}
        payload: Dict[str, Any] = {
            "data": data,
            "recent_form": data["recent_form"],
            "fetched_at_utc": _now_iso(),
            "source_confidence": 0.9 if recent else 0.5,
        }
        return payload

