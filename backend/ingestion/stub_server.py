"""
Local stub HTTP server for live connector testing.
Serves fixture data via HTTP endpoints to simulate a live API.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse


def _load_fixtures(fixtures_dir: Path) -> List[Dict[str, Any]]:
    """Load all JSON fixtures from directory (deterministic order)."""
    if not fixtures_dir.exists():
        return []
    files = sorted(fixtures_dir.glob("*.json"))
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


def create_stub_app(fixtures_dir: Path | None = None) -> FastAPI:
    """
    Create FastAPI app that serves fixtures via HTTP endpoints.
    fixtures_dir: path to fixtures directory (default: ingestion/fixtures/stub_platform).
    """
    if fixtures_dir is None:
        # backend/ingestion/stub_server.py -> backend/ingestion/fixtures/stub_platform
        base = Path(__file__).resolve().parent.parent
        fixtures_dir = base / "ingestion" / "fixtures" / "stub_platform"
    fixtures_dir = Path(fixtures_dir)
    fixtures = _load_fixtures(fixtures_dir)

    app = FastAPI(title="Stub Platform API", version="1.0.0")

    @app.get("/matches", summary="List all matches")
    async def list_matches() -> List[Dict[str, Any]]:
        """Return all matches (fixtures)."""
        return fixtures

    @app.get("/matches/{match_id}", summary="Get match by ID")
    async def get_match(match_id: str) -> Dict[str, Any]:
        """Return match data for given match_id."""
        for fixture in fixtures:
            fid = str(fixture.get("match_id") or fixture.get("id", ""))
            if fid == match_id:
                return fixture
        raise HTTPException(status_code=404, detail=f"Match {match_id!r} not found")

    @app.get("/health", summary="Health check")
    async def health() -> Dict[str, Any]:
        """Health check endpoint."""
        return {"status": "ok", "fixtures_count": len(fixtures)}

    return app
