"""
Connector registry: resolve connector by name.

No side effects; no DB writes or network calls at registration.
"""

from __future__ import annotations

from typing import Dict, Optional

from .connectors.base import DataConnector
from .connectors.dummy import DummyConnector

_REGISTRY: Dict[str, DataConnector] = {
    "dummy": DummyConnector(),
}


def get_connector(name: str) -> DataConnector:
    """Return the connector registered under the given name. Raises KeyError if unknown."""
    if name not in _REGISTRY:
        raise KeyError(f"Unknown connector: {name}")
    return _REGISTRY[name]


def register_connector(name: str, connector: DataConnector) -> None:
    """Register a connector by name (for tests or future extensions)."""
    _REGISTRY[name] = connector


def list_connector_names() -> list[str]:
    """Return list of registered connector names."""
    return list(_REGISTRY.keys())
