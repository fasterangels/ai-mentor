"""
Local deterministic HTTP stub server for live connector testing.
Offline-friendly, no randomness. Supports failure modes via query param or header (mode=ok|timeout|500|rate_limit|slow).
"""

from __future__ import annotations

import asyncio
from typing import Any, Dict, List

from fastapi import FastAPI, Header, HTTPException, Query

# Deterministic durations (seconds) for timeout/slow modes
STUB_TIMEOUT_SLEEP = 3.0   # sleep longer than client timeout to force timeout
STUB_SLOW_SLEEP = 0.5      # slow but within typical client timeout

# Fixed match list: stable IDs and UTC kickoff (deterministic, no randomness)
STUB_MATCHES: List[Dict[str, Any]] = [
    {
        "match_id": "stub_live_001",
        "home_team": "Alpha FC",
        "away_team": "Beta United",
        "competition": "Stub Live League",
        "kickoff_utc": "2025-10-01T18:00:00+00:00",
        "status": "scheduled",
    },
    {
        "match_id": "stub_live_002",
        "home_team": "Gamma City",
        "away_team": "Delta Town",
        "competition": "Stub Live League",
        "kickoff_utc": "2025-10-02T19:30:00+00:00",
        "status": "scheduled",
    },
]

STUB_ODDS: Dict[str, Dict[str, float]] = {
    "stub_live_001": {"home": 2.20, "draw": 3.30, "away": 3.10},
    "stub_live_002": {"home": 1.95, "draw": 3.50, "away": 3.80},
}


def _get_mode(mode: str | None = Query(None, alias="mode"), x_stub_mode: str | None = Header(None)) -> str:
    """Resolve mode from query param or header. Default ok. Explicit and stable."""
    m = (mode or x_stub_mode or "ok").strip().lower()
    if m not in ("ok", "timeout", "500", "rate_limit", "slow"):
        return "ok"
    return m


def create_stub_app() -> FastAPI:
    """Create FastAPI app for local stub server with deterministic failure modes."""

    app = FastAPI(title="Stub Live Server", version="1.0.0")

    @app.get("/health", summary="Health check")
    async def health(
        mode: str | None = Query(None, alias="mode"),
        x_stub_mode: str | None = Header(None),
    ) -> Dict[str, str]:
        m = _get_mode(mode, x_stub_mode)
        if m == "timeout":
            await asyncio.sleep(STUB_TIMEOUT_SLEEP)
        elif m == "500":
            raise HTTPException(status_code=500, detail="Stub mode=500")
        elif m == "rate_limit":
            raise HTTPException(status_code=429, detail="Rate limited", headers={"Retry-After": "1"})
        elif m == "slow":
            await asyncio.sleep(STUB_SLOW_SLEEP)
        return {"status": "ok"}

    @app.get("/matches", summary="List matches")
    async def list_matches(
        mode: str | None = Query(None, alias="mode"),
        x_stub_mode: str | None = Header(None),
    ) -> List[Dict[str, Any]]:
        m = _get_mode(mode, x_stub_mode)
        if m == "timeout":
            await asyncio.sleep(STUB_TIMEOUT_SLEEP)
        elif m == "500":
            raise HTTPException(status_code=500, detail="Stub mode=500")
        elif m == "rate_limit":
            raise HTTPException(status_code=429, detail="Rate limited", headers={"Retry-After": "1"})
        elif m == "slow":
            await asyncio.sleep(STUB_SLOW_SLEEP)
        return list(STUB_MATCHES)

    @app.get("/matches/{match_id}/odds", summary="Get odds for match")
    async def get_odds(
        match_id: str,
        mode: str | None = Query(None, alias="mode"),
        x_stub_mode: str | None = Header(None),
    ) -> Dict[str, float]:
        m = _get_mode(mode, x_stub_mode)
        if m == "timeout":
            await asyncio.sleep(STUB_TIMEOUT_SLEEP)
        elif m == "500":
            raise HTTPException(status_code=500, detail="Stub mode=500")
        elif m == "rate_limit":
            raise HTTPException(status_code=429, detail="Rate limited", headers={"Retry-After": "1"})
        elif m == "slow":
            await asyncio.sleep(STUB_SLOW_SLEEP)
        if match_id not in STUB_ODDS:
            raise HTTPException(status_code=404, detail=f"Match {match_id!r} not found")
        return dict(STUB_ODDS[match_id])

    return app
