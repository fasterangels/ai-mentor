from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict

from .base import BaseSource


class StubStatsSource(BaseSource):
    """Stub stats: implements Source for registry and BaseSource for legacy pipeline."""

    _PRIORITY = 10

    @property
    def source_name(self) -> str:
        return "stub_stats"

    @property
    def name(self) -> str:
        return self.source_name

    @property
    def priority(self) -> int:
        return self._PRIORITY

    @property
    def domain(self) -> str:
        return "stats"

    def supports(self, kind: str) -> bool:
        return kind == "stats"

    def fetch(self, kind: str, query: Dict[str, Any]) -> Dict[str, Any]:
        """Sync fetch for registry (Source protocol)."""
        match_id = query.get("match_id", "")
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

    async def fetch_match(
        self, match_id: str, window_hours: int
    ) -> Dict[str, Any]:
        """Legacy async fetch for pipeline."""
        return self.fetch("stats", {"match_id": match_id, "window_hours": window_hours})
