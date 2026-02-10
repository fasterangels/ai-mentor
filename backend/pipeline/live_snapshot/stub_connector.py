"""
Stub live connector that raises LiveIODisabledError on fetch (for tests).
"""

from __future__ import annotations

from ingestion.live_io import LiveIODisabledError


class LiveConnectorStub:
    """Stub that raises LiveIODisabledError on any fetch."""

    def fetch_matches(self) -> None:
        raise LiveIODisabledError("Live connector disabled (stub)")

    def fetch_match_data(self, match_id: str) -> None:
        raise LiveIODisabledError("Live connector disabled (stub)")
