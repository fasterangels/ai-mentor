"""
Tests for ops events: structured events are emitted (logger spy / captured logs).
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

_backend = Path(__file__).resolve().parent.parent.parent
if str(_backend) not in sys.path:
    sys.path.insert(0, str(_backend))

import pytest

from ops.ops_events import (
    OPS_LOGGER_NAME,
    log_decay_fit_end,
    log_decay_fit_skipped_low_support,
    log_decay_fit_start,
    log_decay_fit_written,
    log_pipeline_end,
    log_pipeline_start,
    log_ingestion_source,
    log_evaluation_summary,
    log_guardrail_trigger,
)


def test_ops_logger_name() -> None:
    """Ops events use a dedicated logger name."""
    assert OPS_LOGGER_NAME == "ops_events"


def test_log_pipeline_start_returns_float_and_emits(caplog: pytest.LogCaptureFixture) -> None:
    """log_pipeline_start emits event and returns start time (float)."""
    caplog.set_level(logging.INFO, logger=OPS_LOGGER_NAME)
    t = log_pipeline_start("dummy", "match-1")
    assert isinstance(t, float)
    assert "pipeline_start" in caplog.text
    assert "connector_name" in caplog.text and "match_id" in caplog.text


def test_log_pipeline_end_emits(caplog: pytest.LogCaptureFixture) -> None:
    """log_pipeline_end emits event with duration."""
    caplog.set_level(logging.INFO, logger=OPS_LOGGER_NAME)
    log_pipeline_end("dummy", "match-1", 1.5)
    assert "pipeline_end" in caplog.text
    assert "duration_seconds" in caplog.text
    log_pipeline_end("dummy", "match-2", 0.0, error="NO_FIXTURE")
    assert "NO_FIXTURE" in caplog.text


def test_log_ingestion_source_emits(caplog: pytest.LogCaptureFixture) -> None:
    """log_ingestion_source emits recorded or live source."""
    caplog.set_level(logging.INFO, logger=OPS_LOGGER_NAME)
    log_ingestion_source("sample_platform", "recorded", "m1")
    assert "ingestion_source" in caplog.text
    assert "recorded" in caplog.text
    log_ingestion_source("stub_platform", "live", "m2")
    assert "live" in caplog.text


def test_log_evaluation_summary_emits(caplog: pytest.LogCaptureFixture) -> None:
    """log_evaluation_summary emits counts and optional accuracy."""
    caplog.set_level(logging.INFO, logger=OPS_LOGGER_NAME)
    log_evaluation_summary(10, 8, {"one_x_two": 0.75, "over_under_25": 0.8})
    assert "evaluation_summary" in caplog.text
    assert "match_count" in caplog.text and "resolved_count" in caplog.text
    log_evaluation_summary(0, 0, None)
    assert "match_count" in caplog.text


def test_log_guardrail_trigger_emits(caplog: pytest.LogCaptureFixture) -> None:
    """log_guardrail_trigger emits trigger and detail; optional cap_value."""
    caplog.set_level(logging.INFO, logger=OPS_LOGGER_NAME)
    log_guardrail_trigger("max_fixtures_per_run", "Requested 60; cap 50", cap_value=50)
    assert "guardrail_trigger" in caplog.text
    assert "max_fixtures_per_run" in caplog.text
    assert "50" in caplog.text
    log_guardrail_trigger("live_io_blocked", "LIVE_WRITES_ALLOWED=false")
    assert "live_io_blocked" in caplog.text


def test_log_decay_fit_start_returns_float_and_emits(caplog: pytest.LogCaptureFixture) -> None:
    """log_decay_fit_start emits event and returns start time."""
    caplog.set_level(logging.INFO, logger=OPS_LOGGER_NAME)
    t = log_decay_fit_start()
    assert isinstance(t, float)
    assert "decay_fit_start" in caplog.text


def test_log_decay_fit_end_and_written_emit(caplog: pytest.LogCaptureFixture) -> None:
    """log_decay_fit_end and log_decay_fit_written emit with counts."""
    caplog.set_level(logging.INFO, logger=OPS_LOGGER_NAME)
    log_decay_fit_written(3)
    assert "decay_fit_written" in caplog.text and "3" in caplog.text
    log_decay_fit_end(params_count=3, duration_seconds=0.1, skipped_low_support=0)
    assert "decay_fit_end" in caplog.text and "params_count" in caplog.text


def test_log_decay_fit_skipped_low_support_emits(caplog: pytest.LogCaptureFixture) -> None:
    """log_decay_fit_skipped_low_support emits count."""
    caplog.set_level(logging.INFO, logger=OPS_LOGGER_NAME)
    log_decay_fit_skipped_low_support(2)
    assert "decay_fit_skipped_low_support" in caplog.text and "2" in caplog.text


def test_log_confidence_penalty_shadow_emits(caplog: pytest.LogCaptureFixture) -> None:
    """confidence_penalty_shadow start/end/written emit."""
    from ops.ops_events import (
        log_confidence_penalty_shadow_end,
        log_confidence_penalty_shadow_start,
        log_confidence_penalty_shadow_written,
    )
    caplog.set_level(logging.INFO, logger=OPS_LOGGER_NAME)
    t = log_confidence_penalty_shadow_start()
    assert isinstance(t, float)
    assert "confidence_penalty_shadow_start" in caplog.text
    log_confidence_penalty_shadow_written(5)
    assert "confidence_penalty_shadow_written" in caplog.text and "5" in caplog.text
    log_confidence_penalty_shadow_end(5, 0.1)
    assert "confidence_penalty_shadow_end" in caplog.text and "row_count" in caplog.text
