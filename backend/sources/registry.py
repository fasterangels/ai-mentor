from __future__ import annotations

from typing import Dict, List

from .base import DataSource
from .mock_source import MockSource

_SOURCES: Dict[str, DataSource] = {}


def register_source(source: DataSource) -> None:
    """
    Register a data source implementation by its name.
    """
    _SOURCES[source.name] = source


def get_source(name: str) -> DataSource:
    """
    Retrieve a previously registered data source.
    """
    return _SOURCES[name]


def list_sources() -> List[str]:
    """
    Return a deterministic list of registered source names.
    """
    return sorted(_SOURCES.keys())


# Register built-in sources in a deterministic way.
register_source(MockSource())

