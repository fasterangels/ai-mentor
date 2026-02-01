from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict


class BaseSource(ABC):
    """Base interface for data sources."""

    @property
    @abstractmethod
    def source_name(self) -> str:
        """Unique identifier for this source."""
        pass

    @property
    @abstractmethod
    def domain(self) -> str:
        """Domain this source provides (e.g., 'fixtures', 'stats')."""
        pass

    @abstractmethod
    async def fetch(
        self, match_id: str, window_hours: int
    ) -> Dict[str, Any]:
        """Fetch data for a match.

        Returns:
            Raw payload-like dict with at least:
            - 'data': normalized data structure
            - 'fetched_at_utc': ISO timestamp string
            - 'source_confidence': float (0.0-1.0)
        """
        pass
