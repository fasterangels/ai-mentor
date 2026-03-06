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


class InjuriesLineupsSource(Source):
    """Player injuries/suspensions and expected lineups via football-data.org (v1 simple integration)."""

    _PRIORITY = 45

    @property
    def name(self) -> str:
        return "injuries_lineups"

    @property
    def priority(self) -> int:
        return self._PRIORITY

    def supports(self, kind: str) -> bool:
        return kind in ("injuries", "lineups")

    def fetch(self, kind: str, query: Dict[str, Any]) -> Dict[str, Any]:
        """Fetch injuries or lineups with fail-safe behaviour.

        - Missing API key -> empty payload
        - Network/HTTP/JSON errors -> empty payload
        - Missing required query fields -> empty payload
        """
        api_key = os.getenv("FOOTBALL_DATA_API_KEY") or ""
        if not api_key:
            return self._empty_payload(kind)

        try:
            if kind == "injuries":
                return self._fetch_injuries(query, api_key)
            if kind == "lineups":
                return self._fetch_lineups(query, api_key)
        except (HTTPError, URLError, TimeoutError, ValueError, json.JSONDecodeError):
            return self._empty_payload(kind)

        return self._empty_payload(kind)

    # ------------------------------------------------------------------ helpers

    def _empty_payload(self, kind: str) -> Dict[str, Any]:
        if kind == "injuries":
            data: Dict[str, Any] = {"injuries": []}
        elif kind == "lineups":
            data = {"lineups": {"home": [], "away": []}}
        else:
            data = {}
        payload: Dict[str, Any] = {
            "data": data,
            "fetched_at_utc": _now_iso(),
            "source_confidence": 0.0,
        }
        # Mirror convenience top-level keys for symmetry with other sources.
        payload.update(data)
        return payload

    def _request(self, path: str, params: Dict[str, Any], *, api_key: str) -> Dict[str, Any]:
        """Low-level GET returning JSON object.

        The exact endpoint/shape is abstracted so tests can mock this method.
        """
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

    # ----------------------------- injuries (v1: simple mapping from raw payload)

    def _fetch_injuries(self, query: Dict[str, Any], api_key: str) -> Dict[str, Any]:
        """Fetch injuries/suspensions for both teams; v1 simple mapping."""
        home_team = (query.get("home_team") or "").strip()
        away_team = (query.get("away_team") or "").strip()
        if not (home_team and away_team):
            return self._empty_payload("injuries")

        # Endpoint path and params are kept generic; tests mock _request.
        raw = self._request(
            "/injuries",
            {"home": home_team, "away": away_team},
            api_key=api_key,
        )
        items = raw.get("injuries") or raw.get("items") or []
        if not isinstance(items, list):
            items = []

        normalized: List[Dict[str, Any]] = []
        for r in items:
            if not isinstance(r, dict):
                continue
            team = (r.get("team") or "").strip()
            player = (r.get("player") or r.get("name") or "").strip()
            position = (r.get("position") or "").strip()
            reason = (r.get("reason") or r.get("description") or "").strip()
            status_raw = (r.get("status") or "").strip().lower()
            status = self._normalize_status(status_raw)
            normalized.append(
                {
                    "team": team,
                    "player": player,
                    "position": position,
                    "reason": reason,
                    "status": status,
                }
            )

        data: Dict[str, Any] = {"injuries": normalized}
        payload: Dict[str, Any] = {
            "data": data,
            "injuries": data["injuries"],
            "fetched_at_utc": _now_iso(),
            "source_confidence": 0.9 if normalized else 0.5,
        }
        return payload

    def _normalize_status(self, status: str) -> str:
        if not status:
            return "injured"
        s = status.lower()
        if any(k in s for k in ("suspend", "ban")):
            return "suspended"
        if any(k in s for k in ("doubt", "questionable")):
            return "doubtful"
        # Default bucket: injured
        return "injured"

    # ----------------------------- lineups (v1: simple mapping from raw payload)

    def _fetch_lineups(self, query: Dict[str, Any], api_key: str) -> Dict[str, Any]:
        """Fetch expected lineups for both teams; v1 simple mapping."""
        home_team = (query.get("home_team") or "").strip()
        away_team = (query.get("away_team") or "").strip()
        if not (home_team and away_team):
            return self._empty_payload("lineups")

        raw = self._request(
            "/lineups",
            {"home": home_team, "away": away_team},
            api_key=api_key,
        )
        home_raw = raw.get("home") or []
        away_raw = raw.get("away") or []
        if not isinstance(home_raw, list):
            home_raw = []
        if not isinstance(away_raw, list):
            away_raw = []

        def _norm_side(items: List[Any]) -> List[Dict[str, Any]]:
            out: List[Dict[str, Any]] = []
            for r in items:
                if not isinstance(r, dict):
                    continue
                player = (r.get("player") or r.get("name") or "").strip()
                position = (r.get("position") or "").strip()
                if not player:
                    continue
                out.append({"player": player, "position": position})
            return out

        home_norm = _norm_side(home_raw)
        away_norm = _norm_side(away_raw)

        lineups = {"home": home_norm, "away": away_norm}
        data: Dict[str, Any] = {"lineups": lineups}
        payload: Dict[str, Any] = {
            "data": data,
            "lineups": data["lineups"],
            "fetched_at_utc": _now_iso(),
            "source_confidence": 0.9 if (home_norm or away_norm) else 0.5,
        }
        return payload

