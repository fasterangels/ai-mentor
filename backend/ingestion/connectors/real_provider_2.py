"""
Real provider 2 adapter: recorded-first (fixtures only by default).
Optional live shadow path gated behind REAL_PROVIDER_2_LIVE=true and LIVE_IO_ALLOWED=true
(no live HTTP in tests; recorded fixtures only here).
"""

from __future__ import annotations

import json
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


class RealProvider2Adapter(RecordedPlatformAdapter):
    """
    Recorded-first adapter: reads fixtures from ingestion/fixtures/real_provider_2/*.json.
    Optional live path (not implemented here) would require REAL_PROVIDER_2_LIVE=true and LIVE_IO_ALLOWED=true.
    """

    def __init__(self, fixtures_dir: Path | None = None) -> None:
        if fixtures_dir is None:
            base = Path(__file__).resolve().parent.parent.parent
            fixtures_dir = base / "ingestion" / "fixtures" / "real_provider_2"
        self._fixtures_dir = Path(fixtures_dir)

    @property
    def name(self) -> str:
        return "real_provider_2"

    def load_fixtures(self) -> List[Dict[str, Any]]:
        """Load all JSON fixture files (deterministic order)."""
        if not self._fixtures_dir.exists():
            return []
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
        return fixtures

    def parse_fixture(self, raw: Dict[str, Any]) -> IngestedMatchData:
        """
        Parse raw fixture dict into IngestedMatchData.
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
