"""
Stub live connector: no network; always raises LiveIODisabledError.
Used by the live->snapshot harness by default so no real IO is attempted.
"""

from __future__ import annotations

from typing import List

from ingestion.connectors.platform_base import DataConnector, IngestedMatchData, MatchIdentity
from ingestion.live_io import LiveIODisabledError


class LiveConnectorStub(DataConnector):
    """
    Live connector stub that ALWAYS raises LiveIODisabledError on any fetch.
    No network calls; for harness skeleton fail-fast behavior.
    """

    @property
    def name(self) -> str:
        return "live_connector_stub"

    def fetch_matches(self) -> List[MatchIdentity]:
        raise LiveIODisabledError(
            "Live IO is disabled; harness uses stub connector. Set LIVE_IO_ALLOWED=true to attempt live (stub still raises)."
        )

    def fetch_match_data(self, match_id: str) -> IngestedMatchData | None:
        raise LiveIODisabledError(
            "Live IO is disabled; harness uses stub connector. Set LIVE_IO_ALLOWED=true to attempt live (stub still raises)."
        )
