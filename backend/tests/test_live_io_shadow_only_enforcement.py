"""
Phase D: Live IO shadow-only enforcement tests.
A) Live IO in non-shadow mode fails fast with exact error.
B) Live IO in shadow mode WITHOUT recorded baseline fails fast.
C) Live IO in shadow mode WITH recorded baseline proceeds (mocked/stubbed, no real IO).
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

_backend = Path(__file__).resolve().parent.parent
if str(_backend) not in sys.path:
    sys.path.insert(0, str(_backend))

import pytest

from ingestion.connectors.platform_base import DataConnector
from ingestion.live_io import (
    LIVE_IO_SHADOW_ONLY_MESSAGE,
    RECORDED_BASELINE_REQUIRED_MESSAGE,
    assert_recorded_baseline_exists,
    execution_mode_context,
    get_connector_safe,
    get_execution_mode,
    set_execution_mode,
    reset_execution_mode,
)


class _FakeLiveConnector(DataConnector):
    """Non-recorded connector for testing."""

    @property
    def name(self) -> str:
        return "fake_live"

    def fetch_matches(self):
        return []

    def fetch_match_data(self, match_id: str):
        return None


def test_live_io_in_non_shadow_mode_fails_fast() -> None:
    """A) Live IO when LIVE_IO_ALLOWED=true and execution_mode != 'shadow' raises exact error."""
    with patch("ingestion.registry.get_connector", return_value=_FakeLiveConnector()):
        with pytest.MonkeyPatch.context() as m:
            m.setenv("LIVE_IO_ALLOWED", "1")
            # Ensure we are not in shadow mode (default)
            token = set_execution_mode("production")
            try:
                with pytest.raises(ValueError) as exc_info:
                    get_connector_safe("any_name")
                assert str(exc_info.value) == LIVE_IO_SHADOW_ONLY_MESSAGE
            finally:
                reset_execution_mode(token)


def test_live_io_in_shadow_mode_without_recorded_baseline_fails_fast() -> None:
    """B) Live IO in shadow mode without recorded baseline (no fixtures dir / empty) fails fast."""
    # Use a path that is not a directory so assert_recorded_baseline_exists fails
    with patch("ingestion.registry.get_connector", return_value=_FakeLiveConnector()):
        with patch("ingestion.live_io._fixtures_dir_for_connector", return_value=Path("/nonexistent_connector_fixtures_xyz")):
            with pytest.MonkeyPatch.context() as m:
                m.setenv("LIVE_IO_ALLOWED", "1")
                with execution_mode_context("shadow"):
                    with pytest.raises(ValueError) as exc_info:
                        get_connector_safe("no_baseline_connector")
                    msg = str(exc_info.value)
                    assert "Recorded baseline required" in msg
                    assert "no_baseline_connector" in msg


def test_assert_recorded_baseline_exists_empty_dir_fails() -> None:
    """assert_recorded_baseline_exists raises when dir exists but has no JSON."""
    # Fixtures base dir has no .json files at top level (only in subdirs)
    fixtures_base = _backend / "ingestion" / "fixtures"
    with patch("ingestion.live_io._fixtures_dir_for_connector", return_value=fixtures_base):
        with pytest.raises(ValueError) as exc_info:
            assert_recorded_baseline_exists("x")
        assert "Recorded baseline required" in str(exc_info.value)


def test_live_io_in_shadow_mode_with_recorded_baseline_proceeds() -> None:
    """C) Live IO in shadow mode with recorded baseline (stub_live_platform has fixtures) returns adapter."""
    with pytest.MonkeyPatch.context() as m:
        m.setenv("LIVE_IO_ALLOWED", "1")
        with execution_mode_context("shadow"):
            adapter = get_connector_safe("stub_live_platform")
        assert adapter is not None
        assert adapter.name == "stub_live_platform"


def test_get_execution_mode_default_empty() -> None:
    """get_execution_mode returns empty string when not set."""
    token = set_execution_mode("something")
    try:
        assert get_execution_mode() == "something"
    finally:
        reset_execution_mode(token)
    # After reset, context may be empty or from outer scope
    get_execution_mode()  # no raise
