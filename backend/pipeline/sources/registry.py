"""Default registry and fetch(kind, query) with filesystem cache."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from .base import (
    SourceRegistry,
    get_cache_path,
    get_cache_ttl_seconds,
    read_cached,
    write_cached,
)

_CACHE_ROOT = Path(__file__).resolve().parent.parent.parent / "runtime" / "source_cache"

_default_registry: SourceRegistry | None = None


def get_registry() -> SourceRegistry:
    """Return the default source registry (singleton)."""
    global _default_registry
    if _default_registry is None:
        _default_registry = SourceRegistry()
    return _default_registry


def fetch(
    kind: str,
    query: Dict[str, Any],
    cache_root: Path | None = None,
    force_refresh: bool = False,
) -> Dict[str, Any]:
    """Fetch merged payload for kind/query; use cache if valid (unless force_refresh), else fetch_all + merge + cache."""
    root = cache_root if cache_root is not None else _CACHE_ROOT
    ttl = get_cache_ttl_seconds()
    path = get_cache_path(root, kind, query)
    if not force_refresh:
        cached = read_cached(path, ttl)
        if cached is not None:
            return cached
    reg = get_registry()
    results = reg.fetch_all(kind, query)
    merged = reg.merge_payloads(kind, results)
    write_cached(path, merged)
    return merged
