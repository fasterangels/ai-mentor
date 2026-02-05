"""
Stub live platform connector: fetches from local dev stub server.
LIVE connector (recorded-first policy applies). Fails fast if LIVE_IO_ALLOWED is not set.
Supports STUB_LIVE_MODE (ok|timeout|500|rate_limit|slow) for deterministic failure drills.
"""

from __future__ import annotations

import os
import time
from datetime import datetime, timezone
from typing import Any, Dict, List
from urllib.parse import urljoin

import httpx

from ingestion.connectors.platform_base import DataConnector, IngestedMatchData, MatchIdentity
from ingestion.live_io import (
    LiveIOCircuitOpenError,
    LiveIOFailureError,
    LiveIORateLimitedError,
    LiveIOTimeoutError,
    circuit_breaker_allow_request,
    circuit_breaker_record_failure,
    circuit_breaker_record_success,
    live_io_allowed,
    record_request,
)


def _stub_mode() -> str:
    """Stub mode from env (default ok). Explicit and stable for drills."""
    m = (os.environ.get("STUB_LIVE_MODE") or "ok").strip().lower()
    if m not in ("ok", "timeout", "500", "rate_limit", "slow"):
        return "ok"
    return m


def _timeout_seconds() -> float:
    """Request timeout; small for failure drills when env set."""
    try:
        v = os.environ.get("LIVE_IO_TIMEOUT_SECONDS")
        if v is not None and v.strip():
            return float(v.strip())
    except ValueError:
        pass
    return 5.0


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
    Not a RecordedPlatformAdapter; requires LIVE_IO_ALLOWED=true.
    STUB_LIVE_MODE (ok|timeout|500|rate_limit|slow) and LIVE_IO_TIMEOUT_SECONDS for drills.
    """

    def __init__(self, base_url: str | None = None) -> None:
        base_url = base_url or "http://localhost:8001"
        self._base_url = str(base_url).rstrip("/")
        self._timeout = _timeout_seconds()
        self._client = httpx.Client(base_url=self._base_url, timeout=self._timeout)

    @property
    def name(self) -> str:
        return "stub_live_platform"

    def _require_live_io(self) -> None:
        from ingestion.live_io import live_io_allowed
        if not live_io_allowed():
            raise RuntimeError("stub_live_platform is a LIVE connector; set LIVE_IO_ALLOWED=true to use it")

    def _get(self, path: str) -> Any:
        if not circuit_breaker_allow_request():
            record_request(success=False, latency_ms=0.0, circuit_open=True)
            raise LiveIOCircuitOpenError("Circuit open")
        mode = _stub_mode()
        url = urljoin(self._base_url + "/", path.lstrip("/"))
        if "?" in url:
            url = f"{url}&mode={mode}"
        else:
            url = f"{url}?mode={mode}"
        t0 = time.perf_counter()
        try:
            r = self._client.get(url, timeout=self._timeout)
            latency_ms = (time.perf_counter() - t0) * 1000
            if r.status_code == 429:
                record_request(success=False, latency_ms=latency_ms, rate_limited=True)
                circuit_breaker_record_failure()
                raise LiveIORateLimitedError(f"429 Rate Limited: {r.text}")
            if r.status_code >= 500:
                record_request(success=False, latency_ms=latency_ms)
                circuit_breaker_record_failure()
                raise LiveIOFailureError(f"HTTP {r.status_code}: {r.text}")
            r.raise_for_status()
            record_request(success=True, latency_ms=latency_ms)
            circuit_breaker_record_success()
            return r.json()
        except httpx.TimeoutException as e:
            latency_ms = (time.perf_counter() - t0) * 1000
            record_request(success=False, latency_ms=latency_ms, timeout=True)
            circuit_breaker_record_failure()
            raise LiveIOTimeoutError("Request timed out") from e
        except (LiveIORateLimitedError, LiveIOFailureError, LiveIOTimeoutError, LiveIOCircuitOpenError):
            raise
        except httpx.HTTPStatusError as e:
            latency_ms = (time.perf_counter() - t0) * 1000
            if e.response.status_code == 404:
                record_request(success=False, latency_ms=latency_ms)
                return None
            record_request(success=False, latency_ms=latency_ms)
            circuit_breaker_record_failure()
            raise ValueError(f"HTTP {e.response.status_code}: {e.response.text}") from e
        except httpx.RequestError as e:
            latency_ms = (time.perf_counter() - t0) * 1000
            record_request(success=False, latency_ms=latency_ms)
            circuit_breaker_record_failure()
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
