from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict

from .base import BaseSource


class StubFixturesSource(BaseSource):
    """Stub implementation for fixtures data source.

    Returns deterministic mock data for testing/development.
    """

    @property
    def source_name(self) -> str:
        return "stub_fixtures"

    @property
    def domain(self) -> str:
        return "fixtures"

    async def fetch(
        self, match_id: str, window_hours: int
    ) -> Dict[str, Any]:
        """Return deterministic stub fixtures data."""
        # Deterministic mock data based on match_id
        # TODO: Replace with real source integration
        return {
            "data": {
                "match_id": match_id,
                "home_team": "Team A",
                "away_team": "Team B",
                "kickoff_utc": "2026-02-01T18:00:00Z",
                "venue": "Stadium X",
                "competition": "League Y",
                "status": "scheduled",
            },
            "fetched_at_utc": datetime.now(timezone.utc).isoformat(),
            "source_confidence": 0.9,
        }
