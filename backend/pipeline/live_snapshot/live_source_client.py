"""
Live source client abstraction for G1: read from live (or fake) source only.
No analysis, no decisions. Used only by live-shadow adapter to fetch and snapshot.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Protocol


class LiveSourceClient(Protocol):
    """Protocol for fetching raw fixture/payload data from a live or simulated source."""

    def fetch_fixtures(self) -> List[Dict[str, Any]]:
        """Return list of raw fixture payloads (each dict JSON-serializable). No network if stub/fake."""
        ...

    def fetch_fixture_detail(self, fixture_id: str) -> Optional[Dict[str, Any]]:
        """Return one fixture detail payload or None. Optional for clients that only support fetch_fixtures."""
        ...


class NullLiveClient:
    """No-op client: returns empty list. No network. Use when live-shadow should do nothing."""

    def fetch_fixtures(self) -> List[Dict[str, Any]]:
        return []

    def fetch_fixture_detail(self, fixture_id: str) -> Optional[Dict[str, Any]]:
        return None


class FakeLiveClient:
    """
    Deterministic fake client for tests. No network. Returns fixed payloads.
    Use in CI and integration tests only.
    """

    def __init__(
        self,
        fixtures: Optional[List[Dict[str, Any]]] = None,
        name: str = "fake_live",
    ) -> None:
        self._fixtures = list(fixtures) if fixtures else []
        self._name = name

    def fetch_fixtures(self) -> List[Dict[str, Any]]:
        return list(self._fixtures)

    def fetch_fixture_detail(self, fixture_id: str) -> Optional[Dict[str, Any]]:
        for f in self._fixtures:
            fid = f.get("fixture_id") or f.get("match_id") or f.get("id")
            if str(fid) == str(fixture_id):
                return dict(f)
        return None
