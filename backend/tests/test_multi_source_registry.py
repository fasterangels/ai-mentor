"""
Tests for multi-source registry: priority, deterministic merge, cache (no network).
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict

_backend = Path(__file__).resolve().parent.parent
_repo_root = _backend.parent
for _p in (_backend, _repo_root):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from backend.pipeline.sources.base import Source, SourceRegistry, get_cache_key, get_cache_path


class CountingSource:
    """Minimal Source that counts fetch calls and returns fixed payload."""

    def __init__(self, name: str, priority: int, kind: str) -> None:
        self._name = name
        self._priority = priority
        self._kind = kind
        self.fetch_count = 0

    @property
    def name(self) -> str:
        return self._name

    @property
    def priority(self) -> int:
        return self._priority

    def supports(self, kind: str) -> bool:
        return kind == self._kind

    def fetch(self, kind: str, query: Dict[str, Any]) -> Dict[str, Any]:
        self.fetch_count += 1
        return {"value": self._name, "priority": self._priority}


def test_registers_sources_and_respects_priority() -> None:
    """Registry lists sources for a kind sorted by priority descending."""
    reg = SourceRegistry()
    low = CountingSource("low", 1, "test")
    high = CountingSource("high", 10, "test")
    reg.register(low)
    reg.register(high)
    listed = reg.list_sources("test")
    assert len(listed) == 2
    assert listed[0].name == "high"
    assert listed[1].name == "low"
    results = reg.fetch_all("test", {})
    assert len(results) == 2
    assert results[0]["source_name"] == "high"
    assert results[1]["source_name"] == "low"


def test_merge_is_deterministic() -> None:
    """Merged payload: higher-priority overwrites scalars; lists concatenated and deduped."""
    reg = SourceRegistry()
    reg.register(CountingSource("a", 10, "x"))
    reg.register(CountingSource("b", 5, "x"))
    results = reg.fetch_all("x", {})
    merged = reg.merge_payloads("x", results)
    assert merged["value"] == "a"
    assert merged["priority"] == 10
    assert "meta" in merged
    assert len(merged["meta"]["sources"]) == 2
    assert merged["meta"]["sources"][0]["source_name"] == "a"

    # Lists: add a source that returns a list
    class ListSource:
        def __init__(self, name: str, priority: int, items: list) -> None:
            self._name = name
            self._priority = priority
            self._items = items

        @property
        def name(self) -> str:
            return self._name

        @property
        def priority(self) -> int:
            return self._priority

        def supports(self, kind: str) -> bool:
            return kind == "list_kind"

        def fetch(self, kind: str, query: Dict[str, Any]) -> Dict[str, Any]:
            return {"items": self._items}

    reg2 = SourceRegistry()
    reg2.register(ListSource("s1", 10, [{"id": "1", "x": 1}, {"id": "2", "x": 2}]))
    reg2.register(ListSource("s2", 5, [{"id": "2", "x": 99}, {"id": "3", "x": 3}]))
    res = reg2.fetch_all("list_kind", {})
    merged2 = reg2.merge_payloads("list_kind", res)
    items = merged2["items"]
    assert len(items) == 3
    ids = [x["id"] for x in items]
    assert ids == ["1", "2", "3"]


def test_cache_returns_same_payload_without_refetch(monkeypatch, tmp_path: Path) -> None:
    """With cache_root pointing to tmp_path, second fetch returns cached payload and does not call source."""
    from backend.pipeline.sources.registry import fetch, get_registry

    monkeypatch.setenv("SOURCE_CACHE_TTL_SECONDS", "60")
    reg = get_registry()
    src = CountingSource("single", 1, "cached_kind")
    reg.register(src)
    cache_root = tmp_path / "source_cache"
    cache_root.mkdir(parents=True, exist_ok=True)

    first = fetch("cached_kind", {"q": 1}, cache_root=cache_root)
    assert first["value"] == "single"
    assert src.fetch_count == 1

    second = fetch("cached_kind", {"q": 1}, cache_root=cache_root)
    assert second == first
    assert src.fetch_count == 1

    third = fetch("cached_kind", {"q": 2}, cache_root=cache_root)
    assert third["value"] == "single"
    assert src.fetch_count == 2


def test_cache_key_deterministic() -> None:
    """Cache key is deterministic for same kind and query."""
    k1 = get_cache_key("fixtures", {"match_id": "M1"})
    k2 = get_cache_key("fixtures", {"match_id": "M1"})
    assert k1 == k2
    k3 = get_cache_key("fixtures", {"match_id": "M2"})
    assert k1 != k3
    k4 = get_cache_key("stats", {"match_id": "M1"})
    assert k1 != k4


def test_cache_path_under_root() -> None:
    """Cache path is {root}/{kind}/{key}.json."""
    root = Path("/tmp/cache")
    path = get_cache_path(root, "fixtures", {"match_id": "M1"})
    assert path.parent == root / "fixtures"
    assert path.suffix == ".json"
    assert len(path.stem) == 64
