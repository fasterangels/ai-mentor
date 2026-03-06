from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional, Protocol


@dataclass
class FetchRequest:
    """
    Request to fetch data from a named source for a given market.
    """

    source: str
    market: str
    params: Optional[Dict[str, Any]] = None


@dataclass
class FetchResult:
    """
    Result of a data source fetch.
    """

    source: str
    market: str
    fetched_at_iso: str
    payload: Dict[str, Any]


class DataSource(Protocol):
    """
    Minimal protocol for an online data source.
    """

    name: str

    def fetch(self, req: FetchRequest) -> FetchResult:
        ...

