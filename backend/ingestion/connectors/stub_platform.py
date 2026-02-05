"""
Stub platform adapter: fetches from local HTTP stub server (live IO, not recorded).
Requires LIVE_IO_ALLOWED=true. Serves same data as sample_platform but via HTTP.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict, List
from urllib.parse import urljoin

import httpx

from ingestion.connectors.platform_base import DataConnector, IngestedMatchData, MatchIdentity


def _normalize_kickoff_utc(value: str) -> str:
    """Normalize kickoff to ISO8601 UTC. Raises ValueError if missing or invalid."""
    if not value or not isinstance(value, str):
        raise ValueError("kickoff_utc is required and must be a non-empty string")
    s = value.strip().replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(s)
    except ValueError as e:
        raise ValueError(f"kickoff_utc must be ISO8601: {e!s}") from e
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat()


def _parse_odds_1x2(raw: Any) -> Dict[str, float]:
    """Extract 1X2 odds. Required keys: home, draw, away. Raises ValueError if missing."""
    if not isinstance(raw, dict):
        raise ValueError("odds_1x2 must be an object with home, draw, away")
    required = ("home", "draw", "away")
    for k in required:
        if k not in raw:
            raise ValueError(f"odds_1x2 missing required key: {k!r}")
    out: Dict[str, float] = {}
    for k in required:
        v = raw[k]
        try:
            out[k] = float(v)
        except (TypeError, ValueError):
            raise ValueError(f"odds_1x2.{k} must be a number, got {type(v).__name__}")
    return out


class StubPlatformAdapter(DataConnector):
    """
    Adapter that fetches from local HTTP stub server (live IO, requires LIVE_IO_ALLOWED).
    NOT a RecordedPlatformAdapter - uses HTTP requests.
    """

    def __init__(self, base_url: str | None = None) -> None:
        """
        Initialize stub adapter.
        base_url: base URL of stub server (default: http://localhost:8001).
        """
        if base_url is None:
            base_url = "http://localhost:8001"
        # Handle URL objects from TestClient
        base_url_str = str(base_url).rstrip("/")
        self.base_url = base_url_str
        self._client = httpx.Client(base_url=base_url_str, timeout=5.0)

    @property
    def name(self) -> str:
        return "stub_platform"

    def _fetch_json(self, path: str) -> Dict[str, Any]:
        """Fetch JSON from stub server endpoint."""
        url = urljoin(self.base_url + "/", path.lstrip("/"))
        try:
            response = self._client.get(url)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return {}
            raise ValueError(f"HTTP {e.response.status_code}: {e.response.text}") from e
        except httpx.RequestError as e:
            raise ValueError(f"Request failed: {e!s}") from e

    def fetch_matches(self) -> List[MatchIdentity]:
        """Fetch all matches from stub server."""
        data = self._fetch_json("/matches")
        if not isinstance(data, list):
            return []
        identities: List[MatchIdentity] = []
        for raw in data:
            try:
                match_id = str(raw.get("match_id") or raw.get("id", ""))
                if not match_id:
                    continue
                kickoff = raw.get("kickoff_utc")
                competition = raw.get("competition")
                identities.append(MatchIdentity(
                    match_id=match_id,
                    kickoff_utc=str(kickoff) if kickoff else None,
                    competition=str(competition) if competition else None,
                ))
            except (ValueError, KeyError):
                continue
        return sorted(identities, key=lambda m: m.match_id)

    def fetch_match_data(self, match_id: str) -> IngestedMatchData | None:
        """Fetch match data from stub server."""
        data = self._fetch_json(f"/matches/{match_id}")
        if not data or not isinstance(data, dict):
            return None
        return self._parse_match_data(data)

    def _parse_match_data(self, raw: Dict[str, Any]) -> IngestedMatchData:
        """
        Parse raw match dict into IngestedMatchData.
        Required: match_id, home_team, away_team, competition, kickoff_utc, odds_1x2, status.
        Raises ValueError if any required field is missing or invalid.
        """
        match_id = raw.get("match_id") or raw.get("id")
        if match_id is None:
            raise ValueError("match_id is required (or id)")
        match_id = str(match_id).strip()
        if not match_id:
            raise ValueError("match_id cannot be empty")

        home_team = raw.get("home_team")
        if home_team is None:
            raise ValueError("home_team is required")
        home_team = str(home_team).strip()
        if not home_team:
            raise ValueError("home_team cannot be empty")

        away_team = raw.get("away_team")
        if away_team is None:
            raise ValueError("away_team is required")
        away_team = str(away_team).strip()
        if not away_team:
            raise ValueError("away_team cannot be empty")

        competition = raw.get("competition")
        if competition is None:
            raise ValueError("competition is required")
        competition = str(competition).strip()
        if not competition:
            raise ValueError("competition cannot be empty")

        kickoff_utc = raw.get("kickoff_utc")
        if kickoff_utc is None:
            raise ValueError("kickoff_utc is required")
        kickoff_utc = _normalize_kickoff_utc(str(kickoff_utc))

        odds_raw = raw.get("odds_1x2")
        if odds_raw is None:
            raise ValueError("odds_1x2 is required")
        odds_1x2 = _parse_odds_1x2(odds_raw)

        status = raw.get("status")
        if status is None:
            raise ValueError("status is required")
        status = str(status).strip() or "scheduled"

        return IngestedMatchData(
            match_id=match_id,
            home_team=home_team,
            away_team=away_team,
            competition=competition,
            kickoff_utc=kickoff_utc,
            odds_1x2=odds_1x2,
            status=status,
        )

    def close(self) -> None:
        """Close HTTP client."""
        self._client.close()
