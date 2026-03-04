"""
Unit tests for the Decision Engine policy loader/saver.
"""

from __future__ import annotations

import sys
from pathlib import Path

_repo_root = Path(__file__).resolve().parents[2]
if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))

from backend.policies.decision_engine_policy import (  # type: ignore[import-error]
    DEFAULT_THRESHOLD,
    DecisionPolicy,
    load_policy,
    save_policy,
)


def test_load_default_policy_file() -> None:
    """Loading the checked-in default policy JSON should succeed."""
    policy_path = _repo_root / "backend" / "policies" / "decision_engine_policy.json"
    policy = load_policy(str(policy_path))

    # Version may evolve over time; ensure it is a non-empty string.
    assert isinstance(policy.version, str)
    assert policy.version
    assert "default" in policy.thresholds
    # Default threshold should be a valid probability in [0, 1].
    assert 0.0 <= policy.thresholds["default"] <= 1.0


def test_missing_policy_returns_fallback_default(tmp_path: Path) -> None:
    """Missing policy file should yield a default version with default threshold."""
    missing_path = tmp_path / "nonexistent_policy.json"
    policy = load_policy(str(missing_path))

    assert policy.version == "default"
    assert policy.thresholds == {"default": DEFAULT_THRESHOLD}


def test_save_and_reload_policy_round_trip(tmp_path: Path) -> None:
    """Saving then loading a policy should round-trip version and thresholds."""
    path = tmp_path / "policy.json"
    original = DecisionPolicy(
        version="v1",
        thresholds={
            "default": 0.6,
            "one_x_two": 0.58,
        },
    )

    save_policy(original, str(path))
    reloaded = load_policy(str(path))

    assert reloaded.version == original.version
    assert reloaded.thresholds == original.thresholds

