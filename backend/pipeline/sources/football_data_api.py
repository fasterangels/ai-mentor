from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, List
from urllib.error import URLError, HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .base import Source


_BASE_URL = "https://api.football-data.org/v4"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class FootballDataAPISource(Source):
    """Real fixtures / recent matches provider backed by football-data.org."""

    _PRIORITY = 50

    @property
    def name(self) -> str:
        return "football_data_api"

    @property
    def priority(self) -> int:
        # Higher than stubs (10) so real data can override when available.
        return self._PRIORITY

    def supports(self, kind: str) -> bool:
        return kind in ("fixtures", "recent_matches")

    # Public API -----------------------------------------------------------------

    def fetch(self, kind: str, query: Dict[str, Any]) -> Dict[str, Any]:
        """Fetch data for fixtures or recent_matches.

        Fail-safe behaviour:
        - If API key is missing or invalid, return an empty payload.
        - If network/HTTP error occurs, return an empty payload.
        - If required query parameters are missing, return an empty payload.

        The payload always contains a \"data\" key that is compatible with the
        existing pipeline consensus / quality logic, and convenience top-level
        keys (matches / recent_matches) for direct callers.
        """
        api_key = os.getenv("FOOTBALL_DATA_API_KEY") or ""
        if not api_key:
            return self._empty_payload(kind)

        try:
            if kind == "fixtures":
                return self._fetch_fixtures(query, api_key)
            if kind == "recent_matches":
                return self._fetch_recent_matches(query, api_key)
        except (HTTPError, URLError, TimeoutError, ValueError, json.JSONDecodeError):
            return self._empty_payload(kind)

        # Unsupported kind: treat as empty so registry behaviour is consistent.
        return self._empty_payload(kind)

    # Kind implementations -------------------------------------------------------

    def _fetch_fixtures(self, query: Dict[str, Any], api_key: str) -> Dict[str, Any]:
        """Fetch scheduled fixtures for a given home/away pair on a date."""
        team_home = (query.get("team_home") or "").strip().lower()
        team_away = (query.get("team_away") or "").strip().lower()
        date_str = (query.get("date") or "").strip()

        if not (team_home and team_away and date_str):
            return self._empty_payload("fixtures")

        raw = self._request(
            "/matches",
            {
                "dateFrom": date_str,
                "dateTo": date_str,
            },
            api_key=api_key,
        )
        matches_raw: List[Dict[str, Any]] = raw.get("matches") or []
        normalized: List[Dict[str, Any]] = []
        for m in matches_raw:
            home_name = (m.get("homeTeam", {}) or {}).get("name") or ""
            away_name = (m.get("awayTeam", {}) or {}).get("name") or ""
            home_norm = home_name.lower()
            away_norm = away_name.lower()
            if home_norm != team_home or away_norm != team_away:
                continue
            normalized.append(
                {
                    "id": str(m.get("id")),
                    "home_team": home_norm,
                    "away_team": away_norm,
                    "date": m.get("utcDate"),
                    "competition": (m.get("competition", {}) or {}).get("name"),
                    "status": m.get("status", "SCHEDULED"),
                }
            )

        data: Dict[str, Any] = {"matches": normalized}
        confidence = 0.9 if normalized else 0.5
        return {
            "data": data,
            "matches": data["matches"],
            "fetched_at_utc": _now_iso(),
            "source_confidence": confidence,
        }

    def _fetch_recent_matches(self, query: Dict[str, Any], api_key: str) -> Dict[str, Any]:
        """Fetch recent matches for a team id (last 6)."""
        team_id = query.get("team_id")
        if team_id is None:
            return self._empty_payload("recent_matches")

        team_id_str = str(team_id).strip()
        if not team_id_str:
            return self._empty_payload("recent_matches")

        raw = self._request(
            f"/teams/{team_id_str}/matches",
            {
                "limit": "6",
            },
            api_key=api_key,
        )
        matches_raw: List[Dict[str, Any]] = raw.get("matches") or []
        normalized: List[Dict[str, Any]] = []
        for m in matches_raw:
            home_name = (m.get("homeTeam", {}) or {}).get("name") or ""
            away_name = (m.get("awayTeam", {}) or {}).get("name") or ""
            score = (m.get("score", {}) or {}).get("fullTime", {}) or {}
            normalized.append(
                {
                    "home_team": home_name.lower(),
                    "away_team": away_name.lower(),
                    "home_goals": score.get("homeTeam"),
                    "away_goals": score.get("awayTeam"),
                    "date": m.get("utcDate"),
                }
            )

        data: Dict[str, Any] = {"recent_matches": normalized}
        confidence = 0.9 if normalized else 0.5
        return {
            "data": data,
            "recent_matches": data["recent_matches"],
            "fetched_at_utc": _now_iso(),
            "source_confidence": confidence,
        }

    # Helpers --------------------------------------------------------------------

    def _empty_payload(self, kind: str) -> Dict[str, Any]:
        if kind == "fixtures":
            data: Dict[str, Any] = {"matches": []}
        elif kind == "recent_matches":
            data = {"recent_matches": []}
        else:
            data = {}
        # Include both \"data\" and convenience top-level keys where applicable.
        payload: Dict[str, Any] = {
            "data": data,
            "fetched_at_utc": _now_iso(),
            "source_confidence": 0.0,
        }
        payload.update(data)
        return payload

    def _request(self, path: str, params: Dict[str, Any], *, api_key: str) -> Dict[str, Any]:
        """Low-level HTTP GET with JSON decoding."""
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
            return json.loads(body)

