"""Registry resolves dummy connector by name."""

from __future__ import annotations

import sys
from pathlib import Path

_backend = Path(__file__).resolve().parent.parent
if str(_backend) not in sys.path:
    sys.path.insert(0, str(_backend))

from ingestion.connectors.base import DataConnector
from ingestion.connectors.dummy import DummyConnector
from ingestion.registry import get_connector, list_connector_names


def test_registry_resolves_dummy_connector():
    """get_connector('dummy') returns a DataConnector that is a DummyConnector."""
    connector = get_connector("dummy")
    assert isinstance(connector, DataConnector)
    assert isinstance(connector, DummyConnector)


def test_registry_dummy_returns_valid_data():
    """Registry-resolved dummy connector returns valid IngestedMatchData."""
    connector = get_connector("dummy")
    matches = connector.fetch_matches()
    assert len(matches) >= 1
    data = connector.fetch_match_data("dummy-match-1")
    assert data.identity.match_id == "dummy-match-1"


def test_registry_unknown_raises():
    """get_connector with unknown name raises KeyError."""
    import pytest
    with pytest.raises(KeyError, match="Unknown connector"):
        get_connector("nonexistent")


def test_list_connector_names_includes_dummy():
    """list_connector_names includes 'dummy'."""
    names = list_connector_names()
    assert "dummy" in names
