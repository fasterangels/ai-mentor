"""
Abstract base for data connectors.

No implementation logic; subclasses provide fetch_matches and fetch_match_data.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List

from ingestion.schema import IngestedMatchData, MatchIdentity


class DataConnector(ABC):
    """Abstract data connector: fetch match list and per-match normalized data."""

    @abstractmethod
    def fetch_matches(self) -> List[MatchIdentity]:
        """Return list of match identities (source-agnostic)."""
        ...

    @abstractmethod
    def fetch_match_data(self, match_id: str) -> IngestedMatchData:
        """Return full ingested data for one match. Raises if match_id unknown."""
        ...
