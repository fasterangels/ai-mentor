from __future__ import annotations

import hashlib
import json
import os
import time
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Protocol, runtime_checkable

_DEFAULT_CACHE_TTL_SECONDS = 600  # 10 minutes


@runtime_checkable
class Source(Protocol):
    """Protocol for multi-source ingestion: name, priority, supports(kind), fetch(kind, query)."""

    @property
    def name(self) -> str:
        """Unique identifier for this source."""
        ...

    @property
    def priority(self) -> int:
        """Higher value wins when merging; used for deterministic ordering."""
        ...

    def supports(self, kind: str) -> bool:
        """Return True if this source can fulfill requests for `kind` (e.g. 'fixtures', 'stats', 'odds', 'injuries')."""
        ...

    def fetch(self, kind: str, query: Dict[str, Any]) -> Dict[str, Any]:
        """Fetch data for the given kind and query. Returns a payload dict."""
        ...


class SourceRegistry:
    """Register sources, fetch by kind, merge results deterministically."""

    def __init__(self) -> None:
        self._sources: List[Source] = []

    def register(self, source: Source) -> None:
        """Register a source. Duplicate names are allowed (last wins for same name)."""
        self._sources.append(source)

    def list_sources(self, kind: str) -> List[Source]:
        """Return sources that support `kind`, sorted by priority descending."""
        supported = [s for s in self._sources if s.supports(kind)]
        return sorted(supported, key=lambda s: s.priority, reverse=True)

    def fetch_all(self, kind: str, query: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Call each supporting source in priority order; collect payloads and errors."""
        sources = self.list_sources(kind)
        results: List[Dict[str, Any]] = []
        for src in sources:
            try:
                payload = src.fetch(kind, query)
                results.append(
                    {"source_name": src.name, "payload": payload, "error": None}
                )
            except Exception as e:  # noqa: BLE001
                results.append(
                    {"source_name": src.name, "payload": None, "error": str(e)}
                )
        return results

    def merge_payloads(
        self, kind: str, results: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Merge payloads from fetch_all: higher-priority overwrites scalars; lists concatenated and deduped."""
        merged: Dict[str, Any] = {}
        meta_sources: List[Dict[str, Any]] = []
        errors: List[str] = []

        for r in results:
            name = r.get("source_name", "unknown")
            err = r.get("error")
            if err:
                errors.append(f"{name}: {err}")
                continue
            payload = r.get("payload")
            if payload is None:
                continue
            meta_sources.append(
                {"source_name": name, "fetched_at": payload.get("fetched_at_utc")}
            )
            merged = _merge_two(merged, payload)

        merged["meta"] = {
            "sources": meta_sources,
            "errors": errors,
        }
        return merged


def _merge_two(high: Dict[str, Any], low: Dict[str, Any]) -> Dict[str, Any]:
    """Merge low into high: scalars in high overwrite; lists concatenated and deduped."""
    out: Dict[str, Any] = dict(high)
    for k, v in low.items():
        if k in out:
            if isinstance(out[k], dict) and isinstance(v, dict):
                out[k] = _merge_two(out[k], v)
            elif isinstance(out[k], list) and isinstance(v, list):
                out[k] = _dedupe_list(out[k] + v)
            else:
                pass
        else:
            if isinstance(v, dict):
                out[k] = _merge_two({}, v)
            elif isinstance(v, list):
                out[k] = _dedupe_list(list(v))
            else:
                out[k] = v
    return out


def _dedupe_list(items: List[Any]) -> List[Any]:
    """Stable dedupe: by 'id' if present, else by repr(item)."""
    seen: set[Any] = set()
    result: List[Any] = []
    for x in items:
        key = x.get("id") if isinstance(x, dict) else repr(x)
        if key not in seen:
            seen.add(key)
            result.append(x)
    return result


def get_cache_key(kind: str, query: Dict[str, Any]) -> str:
    """Deterministic cache key from kind + JSON-sorted query."""
    raw = kind + json.dumps(query, sort_keys=True)
    return hashlib.sha256(raw.encode()).hexdigest()


def get_cache_path(cache_root: Path, kind: str, query: Dict[str, Any]) -> Path:
    """Path under cache_root for this kind and query."""
    key = get_cache_key(kind, query)
    return cache_root / kind / f"{key}.json"


def get_cache_ttl_seconds() -> int:
    """TTL from env SOURCE_CACHE_TTL_SECONDS or default 10 minutes."""
    val = os.environ.get("SOURCE_CACHE_TTL_SECONDS", "").strip()
    if not val:
        return _DEFAULT_CACHE_TTL_SECONDS
    try:
        return max(0, int(val))
    except ValueError:
        return _DEFAULT_CACHE_TTL_SECONDS


def read_cached(path: Path, ttl_seconds: int) -> Dict[str, Any] | None:
    """Return cached payload if file exists and is not expired, else None."""
    if not path.exists():
        return None
    try:
        if ttl_seconds > 0 and path.stat().st_mtime + ttl_seconds < time.time():
            return None
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return None


def write_cached(path: Path, data: Dict[str, Any]) -> None:
    """Write merged payload to cache path."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, sort_keys=True)


class BaseSource(ABC):
    """Base interface for data sources (legacy async match fetch)."""

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
    async def fetch_match(
        self, match_id: str, window_hours: int
    ) -> Dict[str, Any]:
        """Fetch data for a match (legacy pipeline).

        Returns:
            Raw payload-like dict with at least:
            - 'data': normalized data structure
            - 'fetched_at_utc': ISO timestamp string
            - 'source_confidence': float (0.0-1.0)
        """
        pass
