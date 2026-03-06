"""
Unit tests for baseline immutability helpers.

Focus on BaselineRun hash stability and sensitivity to policy JSON changes.
"""

from __future__ import annotations

import sys
from pathlib import Path

_backend = Path(__file__).resolve().parent.parent.parent
if str(_backend) not in sys.path:
    sys.path.insert(0, str(_backend))

from evaluation.baseline import BaselineRun, build_baseline_run  # noqa: E402


def _sample_policy(version: str = "v0") -> dict:
    return {
        "meta": {
            "version": version,
            "created_at_utc": "2025-01-01T00:00:00+00:00",
            "notes": "test-policy",
        },
        "markets": {
            "one_x_two": {"min_confidence": 0.62},
        },
        "reasons": {},
    }


def _schema_versions() -> dict:
    return {
        "snapshot_envelope": 1,
        "reason_decay": "1",
    }


def test_baseline_hash_stable_for_identical_inputs() -> None:
    """Same inputs -> identical baseline_hash (reproducible baseline)."""
    policy = _sample_policy("v0")
    schemas = _schema_versions()

    run1: BaselineRun = build_baseline_run("v2", policy, schemas)
    run2: BaselineRun = build_baseline_run("v2", policy, schemas)

    assert run1.policy_digest == run2.policy_digest
    assert run1.baseline_hash == run2.baseline_hash


def test_baseline_hash_changes_when_policy_changes() -> None:
    """Changing policy JSON content -> different baseline_hash."""
    schemas = _schema_versions()

    run1: BaselineRun = build_baseline_run("v2", _sample_policy("v0"), schemas)
    run2: BaselineRun = build_baseline_run("v2", _sample_policy("v1"), schemas)

    assert run1.policy_digest != run2.policy_digest
    assert run1.baseline_hash != run2.baseline_hash

