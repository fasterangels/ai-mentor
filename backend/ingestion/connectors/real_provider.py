"""
Real provider connector: recorded-first (fixtures-driven) with optional live shadow path.
By default uses fixtures only; fail fast if fixtures are missing.
Live path gated by REAL_PROVIDER_LIVE=true AND LIVE_IO_ALLOWED=true and required env (BASE_URL, API_KEY).
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from ingestion.connectors.platform_base import (
    IngestedMatchData,
    MatchIdentity,
    RecordedPlatformAdapter,
)


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


def _provider_to_ingested(raw: Dict[str, Any]) -> IngestedMatchData:
    """
    Map provider payload to normalized IngestedMatchData (existing ingestion schema).
    Required: match_id, home_team, away_team, competition, kickoff_utc, odds_1x2, status.
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
    home_team = str(home_team).strip() or "Home"

    away_team = raw.get("away_team")
    if away_team is None:
        raise ValueError("away_team is required")
    away_team = str(away_team).strip() or "Away"

    competition = raw.get("competition")
    if competition is None:
        raise ValueError("competition is required")
    competition = str(competition).strip() or "Competition"

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


def _real_provider_live_enabled() -> bool:
    """True if REAL_PROVIDER_LIVE is set and LIVE_IO_ALLOWED is set."""
    return (
        os.environ.get("REAL_PROVIDER_LIVE", "").strip().lower() in ("1", "true", "yes")
        and os.environ.get("LIVE_IO_ALLOWED", "").strip().lower() in ("1", "true", "yes")
    )


def _real_provider_live_config() -> tuple[str, str]:
    """Return (base_url, api_key). Raises RuntimeError if missing when live is enabled."""
    base_url = (os.environ.get("REAL_PROVIDER_BASE_URL") or "").strip()
    api_key = (os.environ.get("REAL_PROVIDER_API_KEY") or "").strip()
    if not base_url:
        raise RuntimeError("REAL_PROVIDER_LIVE requires REAL_PROVIDER_BASE_URL")
    if not api_key:
        raise RuntimeError("REAL_PROVIDER_LIVE requires REAL_PROVIDER_API_KEY")
    return base_url, api_key


class RealProviderAdapter(RecordedPlatformAdapter):
    """
    Recorded-first adapter: loads from backend/ingestion/fixtures/real_provider/.
    Optional live path when REAL_PROVIDER_LIVE=true and LIVE_IO_ALLOWED=true (requires BASE_URL and API_KEY).
    Fixtures must exist regardless (recorded-first enforcement).
    """

    def __init__(self, fixtures_dir: Path | None = None) -> None:
        if fixtures_dir is None:
            base = Path(__file__).resolve().parent.parent.parent
            fixtures_dir = base / "ingestion" / "fixtures" / "real_provider"
        self._fixtures_dir = Path(fixtures_dir)
        self._ensure_fixtures_exist()

    def _ensure_fixtures_exist(self) -> None:
        """Fail fast if fixtures directory or files are missing (recorded-first)."""
        if not self._fixtures_dir.exists() or not self._fixtures_dir.is_dir():
            raise FileNotFoundError(
                f"real_provider fixtures directory missing: {self._fixtures_dir}. "
                "Recorded-first: add backend/ingestion/fixtures/real_provider/ with JSON fixtures."
            )
        files = list(self._fixtures_dir.glob("*.json"))
        if not files:
            raise FileNotFoundError(
                f"real_provider: no JSON fixtures in {self._fixtures_dir}. "
                "Recorded-first: add at least one fixture file."
            )

    @property
    def name(self) -> str:
        return "real_provider"

    def load_fixtures(self) -> List[Dict[str, Any]]:
        """Load all JSON fixture files (deterministic order). Fixtures must exist."""
        self._ensure_fixtures_exist()
        files = sorted(self._fixtures_dir.glob("*.json"))
        fixtures: List[Dict[str, Any]] = []
        for path in files:
            try:
                text = path.read_text(encoding="utf-8")
                data = json.loads(text)
                if isinstance(data, dict):
                    fixtures.append(data)
            except (json.JSONDecodeError, OSError):
                continue
        if not fixtures:
            raise ValueError(
                f"real_provider: no valid JSON fixtures in {self._fixtures_dir}. "
                "Recorded-first: ensure at least one valid fixture exists."
            )
        return fixtures

    def parse_fixture(self, raw: Dict[str, Any]) -> IngestedMatchData:
        """Parse one raw fixture into IngestedMatchData (same schema as ingestion)."""
        return _provider_to_ingested(raw)

    def _use_live(self) -> bool:
        """True if live fetch is enabled and config is present."""
        if not _real_provider_live_enabled():
            return False
        try:
            _real_provider_live_config()
            return True
        except RuntimeError:
            return False

    def _live_fetch_matches(self) -> List[MatchIdentity]:
        """Live path: fetch matches from provider API. Requires LIVE_IO_ALLOWED and env config."""
        if not _real_provider_live_enabled():
            raise RuntimeError("real_provider live path requires REAL_PROVIDER_LIVE=true and LIVE_IO_ALLOWED=true")
        base_url, api_key = _real_provider_live_config()
        import httpx
        url = f"{base_url.rstrip('/')}/matches"
        with httpx.Client(timeout=30.0) as client:
            r = client.get(url, headers={"Authorization": f"Bearer {api_key}", "X-API-Key": api_key})
            r.raise_for_status()
            data = r.json()
        if not isinstance(data, list):
            return []
        identities: List[MatchIdentity] = []
        for raw in data:
            if not isinstance(raw, dict):
                continue
            try:
                parsed = _provider_to_ingested(raw)
                identities.append(MatchIdentity(
                    match_id=parsed.match_id,
                    kickoff_utc=parsed.kickoff_utc,
                    competition=parsed.competition,
                ))
            except ValueError:
                continue
        return sorted(identities, key=lambda m: m.match_id)

    def _live_fetch_match_data(self, match_id: str) -> IngestedMatchData | None:
        """Live path: fetch one match from provider API."""
        if not _real_provider_live_enabled():
            raise RuntimeError("real_provider live path requires REAL_PROVIDER_LIVE=true and LIVE_IO_ALLOWED=true")
        base_url, api_key = _real_provider_live_config()
        import httpx
        url = f"{base_url.rstrip('/')}/matches/{match_id}"
        with httpx.Client(timeout=30.0) as client:
            r = client.get(url, headers={"Authorization": f"Bearer {api_key}", "X-API-Key": api_key})
            if r.status_code == 404:
                return None
            r.raise_for_status()
            raw = r.json()
        if not isinstance(raw, dict):
            return None
        return _provider_to_ingested(raw)

    def fetch_matches(self) -> List[MatchIdentity]:
        if self._use_live():
            return self._live_fetch_matches()
        return super().fetch_matches()

    def fetch_match_data(self, match_id: str) -> IngestedMatchData | None:
        if self._use_live():
            return self._live_fetch_match_data(match_id)
        return super().fetch_match_data(match_id)
