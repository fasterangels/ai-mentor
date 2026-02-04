"""
Local deterministic HTTP stub server for live connector testing.
Offline-friendly, no randomness. Serves fixed match list and odds.
"""

from __future__ import annotations

from typing import Any, Dict, List

from fastapi import FastAPI, HTTPException

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

# Deterministic odds snapshots per match (all odds > 0)
STUB_ODDS: Dict[str, Dict[str, float]] = {
    "stub_live_001": {"home": 2.20, "draw": 3.30, "away": 3.10},
    "stub_live_002": {"home": 1.95, "draw": 3.50, "away": 3.80},
}


def create_stub_app() -> FastAPI:
    """Create FastAPI app for local stub server."""

    app = FastAPI(title="Stub Live Server", version="1.0.0")

    @app.get("/health", summary="Health check")
    async def health() -> Dict[str, str]:
        """Return 200 with status ok."""
        return {"status": "ok"}

    @app.get("/matches", summary="List matches")
    async def list_matches() -> List[Dict[str, Any]]:
        """Return fixed list of matches with stable IDs and UTC kickoff."""
        return list(STUB_MATCHES)

    @app.get("/matches/{match_id}/odds", summary="Get odds for match")
    async def get_odds(match_id: str) -> Dict[str, float]:
        """Return deterministic odds snapshot for match (all odds > 0)."""
        if match_id not in STUB_ODDS:
            raise HTTPException(status_code=404, detail=f"Match {match_id!r} not found")
        return dict(STUB_ODDS[match_id])

    return app
