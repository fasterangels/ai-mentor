from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict

from .base import DataSource, FetchRequest, FetchResult


@dataclass
class MockSource(DataSource):
    """
    Deterministic in-memory data source used for testing and development.
    """

    name: str = "mock"

    def fetch(self, req: FetchRequest) -> FetchResult:
        now = datetime.now(timezone.utc).isoformat()
        payload: Dict[str, Any] = {
            "market": req.market,
            "items": [
                {
                    "id": 1,
                    "source": self.name,
                    "market": req.market,
                }
            ],
            "note": "mock",
        }
        return FetchResult(
            source=self.name,
            market=req.market,
            fetched_at_iso=now,
            payload=payload,
        )

