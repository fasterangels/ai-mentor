"""
Contract tests for the safe live IO wrapper: recorded-first, read-only default.
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

_backend = Path(__file__).resolve().parent.parent.parent
if str(_backend) not in sys.path:
    sys.path.insert(0, str(_backend))

import pytest

from ingestion.connectors.platform_base import DataConnector, RecordedPlatformAdapter
from ingestion.live_io import (
    get_connector_safe,
    live_io_allowed,
    live_writes_allowed,
)


class _FakeLiveConnector(DataConnector):
    """Non-recorded connector for testing live_io enforcement."""

    @property
    def name(self) -> str:
        return "fake_live"

    def fetch_matches(self):
        return []

    def fetch_match_data(self, match_id: str):
        return None


def test_live_io_allowed_default_false() -> None:
    """live_io_allowed() is False when LIVE_IO_ALLOWED is unset or falsy."""
    with pytest.MonkeyPatch.context() as m:
        m.setenv("LIVE_IO_ALLOWED", "0")
        assert live_io_allowed() is False
    with pytest.MonkeyPatch.context() as m:
        m.setenv("LIVE_IO_ALLOWED", "false")
        assert live_io_allowed() is False


def test_live_io_allowed_true_when_set() -> None:
    """live_io_allowed() is True when LIVE_IO_ALLOWED is 1/true/yes."""
    with pytest.MonkeyPatch.context() as m:
        m.setenv("LIVE_IO_ALLOWED", "1")
        assert live_io_allowed() is True
    with pytest.MonkeyPatch.context() as m:
        m.setenv("LIVE_IO_ALLOWED", "true")
        assert live_io_allowed() is True


def test_live_writes_allowed_default_false() -> None:
    """live_writes_allowed() is False when LIVE_WRITES_ALLOWED is unset or falsy."""
    with pytest.MonkeyPatch.context() as m:
        m.delenv("LIVE_WRITES_ALLOWED", raising=False)
        assert live_writes_allowed() is False
    with pytest.MonkeyPatch.context() as m:
        m.setenv("LIVE_WRITES_ALLOWED", "0")
        assert live_writes_allowed() is False


def test_live_writes_allowed_true_when_set() -> None:
    """live_writes_allowed() is True when LIVE_WRITES_ALLOWED is 1/true/yes."""
    with pytest.MonkeyPatch.context() as m:
        m.setenv("LIVE_WRITES_ALLOWED", "true")
        assert live_writes_allowed() is True


def test_get_connector_safe_unknown_returns_none() -> None:
    """get_connector_safe returns None for unknown connector name."""
    assert get_connector_safe("nonexistent_connector_xyz") is None


def test_get_connector_safe_recorded_allowed_without_live_io() -> None:
    """Recorded (RecordedPlatformAdapter) connector is returned even when LIVE_IO_ALLOWED is false."""
    with pytest.MonkeyPatch.context() as m:
        m.setenv("LIVE_IO_ALLOWED", "0")
        adapter = get_connector_safe("sample_platform")
    assert adapter is not None
    assert isinstance(adapter, RecordedPlatformAdapter)


def test_get_connector_safe_live_blocked_without_live_io() -> None:
    """Non-recorded connector is None when LIVE_IO_ALLOWED is false (patch registry lookup)."""
    with patch("ingestion.registry.get_connector", return_value=_FakeLiveConnector()):
        with pytest.MonkeyPatch.context() as m:
            m.setenv("LIVE_IO_ALLOWED", "0")
            adapter = get_connector_safe("any_name")
        assert adapter is None


def test_get_connector_safe_live_allowed_when_env_set() -> None:
    """Non-recorded connector is returned when LIVE_IO_ALLOWED is true and execution_mode is shadow with baseline."""
    with patch("ingestion.registry.get_connector", return_value=_FakeLiveConnector()):
        with patch("ingestion.live_io._fixtures_dir_for_connector") as mock_fixtures:
            mock_fixtures.return_value = _backend / "ingestion" / "fixtures" / "sample_platform"
            with pytest.MonkeyPatch.context() as m:
                m.setenv("LIVE_IO_ALLOWED", "1")
                from ingestion.live_io import execution_mode_context
                with execution_mode_context("shadow"):
                    adapter = get_connector_safe("any_name")
            assert adapter is not None
            assert not isinstance(adapter, RecordedPlatformAdapter)
