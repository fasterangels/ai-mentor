"""
Unit tests for live IO circuit breaker state transitions (closed, open, half_open).
"""

from __future__ import annotations

import os
import time

import pytest

from ingestion.live_io import (
    circuit_breaker_allow_request,
    circuit_breaker_record_failure,
    circuit_breaker_record_success,
    circuit_breaker_reset,
)


def test_circuit_starts_closed_and_allows_requests() -> None:
    circuit_breaker_reset()
    assert circuit_breaker_allow_request() is True
    assert circuit_breaker_allow_request() is True


def test_circuit_opens_after_threshold_failures() -> None:
    with pytest.MonkeyPatch.context() as m:
        m.setenv("LIVE_IO_CIRCUIT_FAILURE_THRESHOLD", "2")
        m.setenv("LIVE_IO_CIRCUIT_RESET_SECONDS", "10")
        circuit_breaker_reset()
        assert circuit_breaker_allow_request() is True
        circuit_breaker_record_failure()
        assert circuit_breaker_allow_request() is True
        circuit_breaker_record_failure()
        assert circuit_breaker_allow_request() is False
        circuit_breaker_record_failure()
        assert circuit_breaker_allow_request() is False


def test_circuit_success_resets_failures() -> None:
    with pytest.MonkeyPatch.context() as m:
        m.setenv("LIVE_IO_CIRCUIT_FAILURE_THRESHOLD", "3")
        circuit_breaker_reset()
        circuit_breaker_record_failure()
        circuit_breaker_record_failure()
        circuit_breaker_record_success()
        circuit_breaker_record_failure()
        circuit_breaker_record_failure()
        assert circuit_breaker_allow_request() is True
        circuit_breaker_record_failure()
        assert circuit_breaker_allow_request() is False


def test_circuit_transitions_to_half_open_after_reset_interval() -> None:
    with pytest.MonkeyPatch.context() as m:
        m.setenv("LIVE_IO_CIRCUIT_FAILURE_THRESHOLD", "1")
        m.setenv("LIVE_IO_CIRCUIT_RESET_SECONDS", "0.1")
        circuit_breaker_reset()
        circuit_breaker_record_failure()
        assert circuit_breaker_allow_request() is False
        time.sleep(0.15)
        assert circuit_breaker_allow_request() is True
        circuit_breaker_record_success()
        assert circuit_breaker_allow_request() is True


def test_circuit_half_open_failure_reopens() -> None:
    with pytest.MonkeyPatch.context() as m:
        m.setenv("LIVE_IO_CIRCUIT_FAILURE_THRESHOLD", "1")
        m.setenv("LIVE_IO_CIRCUIT_RESET_SECONDS", "0.1")
        circuit_breaker_reset()
        circuit_breaker_record_failure()
        assert circuit_breaker_allow_request() is False
        time.sleep(0.15)
        assert circuit_breaker_allow_request() is True
        circuit_breaker_record_failure()
        assert circuit_breaker_allow_request() is False
