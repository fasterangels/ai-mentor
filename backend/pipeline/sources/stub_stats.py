from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict

from .base import BaseSource


class StubStatsSource(BaseSource):
    """Stub implementation for statistics data source.

    Returns deterministic mock data for testing/development.
    """

    @property
    def source_name(self) -> str:
        return "stub_stats"

    @property
    def domain(self) -> str:
        return "stats"

    async def fetch(
        self, match_id: str, window_hours: int
    ) -> Dict[str, Any]:
        """Return deterministic stub statistics data."""
        # Deterministic mock data based on match_id
        # TODO: Replace with real source integration
        return {
            "data": {
                "match_id": match_id,
                "home_team_stats": {
                    "goals_scored": 1.8,
                    "goals_conceded": 1.2,
                    "shots_per_game": 12.5,
                    "possession_avg": 55.0,
                },
                "away_team_stats": {
                    "goals_scored": 1.5,
                    "goals_conceded": 1.3,
                    "shots_per_game": 11.2,
                    "possession_avg": 45.0,
                },
                "head_to_head": {
                    "matches_played": 5,
                    "home_wins": 3,
                    "away_wins": 1,
                    "draws": 1,
                },
            },
            "fetched_at_utc": datetime.now(timezone.utc).isoformat(),
            "source_confidence": 0.85,
        }
