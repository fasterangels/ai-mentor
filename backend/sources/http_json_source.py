from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .base import DataSource, FetchRequest, FetchResult


@dataclass
class HttpJsonSource(DataSource):
    """
    Generic HTTP JSON data source backed by urllib from the stdlib.
    """

    name: str
    base_url: str
    timeout: int = 10

    def fetch(self, req: FetchRequest) -> FetchResult:
        params: Dict[str, Any] = {"market": req.market}
        if req.params:
            # Deterministic ordering of query parameters.
            params.update(req.params)
        query_items = [(k, params[k]) for k in sorted(params.keys())]
        query = urlencode(query_items, doseq=True)

        url = f"{self.base_url}?{query}"
        request = Request(url, headers={"User-Agent": "ai-mentor-http-json-source"})
        with urlopen(request, timeout=self.timeout) as resp:  # type: ignore[arg-type]
            raw = resp.read()

        payload: Any = json.loads(raw.decode("utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("Expected JSON object from HTTP JSON source")

        now = datetime.now(timezone.utc).isoformat()
        return FetchResult(
            source=self.name,
            market=req.market,
            fetched_at_iso=now,
            payload=payload,
        )

