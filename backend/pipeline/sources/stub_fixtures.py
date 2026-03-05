from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict

from .base import BaseSource


class StubFixturesSource(BaseSource):
    """Stub fixtures: implements Source for registry and BaseSource for legacy pipeline."""

    _PRIORITY = 10

    @property
    def source_name(self) -> str:
        return "stub_fixtures"

    @property
    def name(self) -> str:
        return self.source_name

    @property
    def priority(self) -> int:
        return self._PRIORITY

    @property
    def domain(self) -> str:
        return "fixtures"

    def supports(self, kind: str) -> bool:
        return kind == "fixtures"

    def fetch(self, kind: str, query: Dict[str, Any]) -> Dict[str, Any]:
        """Sync fetch for registry (Source protocol)."""
        match_id = query.get("match_id", "")
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

    async def fetch_match(
        self, match_id: str, window_hours: int
    ) -> Dict[str, Any]:
        """Legacy async fetch for pipeline."""
        return self.fetch("fixtures", {"match_id": match_id, "window_hours": window_hours})
