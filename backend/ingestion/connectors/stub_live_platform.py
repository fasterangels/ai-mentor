"""
Stub live platform connector: fetches from local dev stub server.
LIVE connector (recorded-first policy applies). Fails fast if LIVE_IO_ALLOWED is not set.
Outputs normalized IngestedMatchData using existing ingestion schema.
"""

from __future__ import annotations

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
    """Extract 1X2 odds. Required keys: home, draw, away; all values > 0."""
    if not isinstance(raw, dict):
        raise ValueError("odds_1x2 must be an object with home, draw, away")
    required = ("home", "draw", "away")
    out: Dict[str, float] = {}
    for k in required:
        if k not in raw:
            raise ValueError(f"odds_1x2 missing required key: {k!r}")
        v = raw[k]
        try:
            val = float(v)
            if val <= 0:
                raise ValueError(f"odds_1x2.{k} must be > 0")
            out[k] = val
        except (TypeError, ValueError):
            raise ValueError(f"odds_1x2.{k} must be a number > 0, got {type(v).__name__}")
    return out


class StubLivePlatformAdapter(DataConnector):
    """
    LIVE connector: fetches from local dev stub server.
    Not a RecordedPlatformAdapter; requires LIVE_IO_ALLOWED=true (get_connector_safe returns None otherwise).
    Fails fast if used without LIVE_IO_ALLOWED (e.g. direct get_connector bypass).
    """

    def __init__(self, base_url: str | None = None) -> None:
        base_url = base_url or "http://localhost:8001"
        self._base_url = str(base_url).rstrip("/")
        self._client = httpx.Client(base_url=self._base_url, timeout=5.0)

    @property
    def name(self) -> str:
        return "stub_live_platform"

    def _require_live_io(self) -> None:
        """Fail fast if LIVE_IO_ALLOWED is not enabled."""
        from ingestion.live_io import live_io_allowed
        if not live_io_allowed():
            raise RuntimeError("stub_live_platform is a LIVE connector; set LIVE_IO_ALLOWED=true to use it")

    def _get(self, path: str) -> Any:
        url = urljoin(self._base_url + "/", path.lstrip("/"))
        try:
            r = self._client.get(url)
            r.raise_for_status()
            return r.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return None
            raise ValueError(f"HTTP {e.response.status_code}: {e.response.text}") from e
        except httpx.RequestError as e:
            raise ValueError(f"Request failed: {e!s}") from e

    def fetch_matches(self) -> List[MatchIdentity]:
        self._require_live_io()
        data = self._get("/matches")
        if not isinstance(data, list):
            return []
        identities: List[MatchIdentity] = []
        for raw in data:
            if not isinstance(raw, dict):
                continue
            match_id = raw.get("match_id") or raw.get("id")
            if not match_id:
                continue
            kickoff = raw.get("kickoff_utc")
            competition = raw.get("competition")
            identities.append(MatchIdentity(
                match_id=str(match_id),
                kickoff_utc=str(kickoff) if kickoff else None,
                competition=str(competition) if competition else None,
            ))
        return sorted(identities, key=lambda m: m.match_id)

    def fetch_match_data(self, match_id: str) -> IngestedMatchData | None:
        self._require_live_io()
        matches = self._get("/matches")
        if not isinstance(matches, list):
            return None
        match_raw: Dict[str, Any] | None = None
        for m in matches:
            if not isinstance(m, dict):
                continue
            mid = m.get("match_id") or m.get("id")
            if str(mid) == str(match_id):
                match_raw = m
                break
        if not match_raw:
            return None
        odds = self._get(f"/matches/{match_id}/odds")
        if not isinstance(odds, dict):
            return None
        odds_1x2 = _parse_odds_1x2(odds)
        match_id_str = str(match_raw.get("match_id") or match_raw.get("id", "")).strip()
        home_team = str(match_raw.get("home_team", "")).strip() or "Home"
        away_team = str(match_raw.get("away_team", "")).strip() or "Away"
        competition = str(match_raw.get("competition", "")).strip() or "Stub Live League"
        kickoff_utc = match_raw.get("kickoff_utc")
        if not kickoff_utc:
            raise ValueError("kickoff_utc is required")
        kickoff_utc = _normalize_kickoff_utc(str(kickoff_utc))
        status = str(match_raw.get("status", "scheduled")).strip() or "scheduled"
        return IngestedMatchData(
            match_id=match_id_str,
            home_team=home_team,
            away_team=away_team,
            competition=competition,
            kickoff_utc=kickoff_utc,
            odds_1x2=odds_1x2,
            status=status,
        )

    def close(self) -> None:
        self._client.close()
