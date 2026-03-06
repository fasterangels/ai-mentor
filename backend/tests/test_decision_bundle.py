"""
Unit tests for the versioned Decision Bundle artifact loader.
"""

from __future__ import annotations

import sys
from pathlib import Path

_repo_root = Path(__file__).resolve().parents[2]
if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))

from backend.runtime.decision_bundle import (  # type: ignore[import-error]
    DecisionBundle,
    load_bundle,
    save_bundle,
)


def test_load_default_when_missing(tmp_path: Path) -> None:
    missing_path = tmp_path / "nonexistent_bundle.json"
    assert not missing_path.exists()

    bundle = load_bundle(str(missing_path))

    assert bundle.version == "default"
    assert bundle.policy_path == "backend/policies/decision_engine_policy.json"
    assert bundle.calibrator_path == "backend/calibration/confidence_calibrator.json"
    assert bundle.reliability_window == "90d"
    assert bundle.meta == {}


def test_save_and_load_roundtrip(tmp_path: Path) -> None:
    path = tmp_path / "bundle.json"
    original = DecisionBundle(
        version="v1",
        policy_path="backend/policies/custom_policy.json",
        calibrator_path="backend/calibration/custom_calibrator.json",
        reliability_window="30d",
        meta={"notes": "test bundle"},
    )

    save_bundle(original, str(path))
    reloaded = load_bundle(str(path))

    assert reloaded.version == original.version
    assert reloaded.policy_path == original.policy_path
    assert reloaded.calibrator_path == original.calibrator_path
    assert reloaded.reliability_window == original.reliability_window
    assert reloaded.meta == original.meta

