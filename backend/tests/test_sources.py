from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict

_repo_root = Path(__file__).resolve().parents[2]
if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))

from backend.sources.base import FetchRequest  # type: ignore[import-error]
from backend.sources.http_json_source import HttpJsonSource  # type: ignore[import-error]
from backend.sources.mock_source import MockSource  # type: ignore[import-error]
from backend.sources.registry import get_source, list_sources  # type: ignore[import-error]


def test_mock_source_fetch_deterministic() -> None:
    source = MockSource()
    req = FetchRequest(source=source.name, market="JPX")
    result = source.fetch(req)

    assert result.source == "mock"
    assert result.market == "JPX"
    assert "T" in result.fetched_at_iso  # ISO-8601-ish timestamp

    expected_payload = {
        "market": "JPX",
        "items": [
            {
                "id": 1,
                "source": "mock",
                "market": "JPX",
            }
        ],
        "note": "mock",
    }
    assert result.payload == expected_payload


def test_registry_list_and_get() -> None:
    names = list_sources()
    assert "mock" in names
    # list_sources returns a deterministic sorted list, so "mock" should be first
    assert names[0] == "mock"

    source = get_source("mock")
    req = FetchRequest(source=source.name, market="US")
    result = source.fetch(req)
    assert result.payload["market"] == "US"
    assert result.payload["note"] == "mock"


def test_http_json_source_url_build(monkeypatch) -> None:
    captured: Dict[str, Any] = {}

    class FakeResponse:
        def __init__(self, url: str) -> None:
            self.url = url

        def read(self) -> bytes:
            return json.dumps({"ok": True}).encode("utf-8")

        def __enter__(self) -> "FakeResponse":
            return self

        def __exit__(self, exc_type, exc, tb) -> None:  # type: ignore[override]
            return None

    def fake_urlopen(request, timeout: int = 10):  # type: ignore[override]
        url = getattr(request, "full_url", str(request))
        captured["url"] = url
        return FakeResponse(url)

    monkeypatch.setattr("backend.sources.http_json_source.urlopen", fake_urlopen)

    src = HttpJsonSource(name="http_test", base_url="https://api.example.com/data", timeout=5)
    req = FetchRequest(source="http_test", market="US", params={"q": "abc", "page": 2})
    result = src.fetch(req)

    assert result.payload == {"ok": True}

    # Deterministic query parameter ordering: market, page, q
    expected_url = "https://api.example.com/data?market=US&page=2&q=abc"
    assert captured["url"] == expected_url

