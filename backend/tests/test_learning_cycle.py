"""
Unit tests for the automated learning cycle runner.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

_repo_root = Path(__file__).resolve().parents[2]
if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))

from backend.automation.learning_cycle import run_learning_cycle  # type: ignore[import-error]
from backend.runtime.decision_bundle import load_bundle  # type: ignore[import-error]


def test_run_learning_cycle_updates_bundle_and_policy(tmp_path: Path) -> None:
    # Create a synthetic evaluation report with a small number of predictions.
    report_path = tmp_path / "evaluation_report.json"
    report = {
        "predictions": [
            {"id": "p1", "market": "A", "score": 0.9, "outcome": 1},
            {"id": "p2", "market": "A", "score": 0.8, "outcome": 1},
            {"id": "p3", "market": "A", "score": 0.4, "outcome": 0},
            {"id": "p4", "market": "B", "score": 0.7, "outcome": 1},
            {"id": "p5", "market": "B", "score": 0.3, "outcome": 0},
        ]
    }
    report_path.write_text(json.dumps(report))

    # Record current bundle version
    bundle_path = "backend/runtime/decision_bundle.json"
    old_bundle = load_bundle(bundle_path)
    old_version = old_bundle.version

    # Run the learning cycle
    result = run_learning_cycle(str(report_path))

    # Bundle should have a new version with an "_auto" suffix and differ from old version.
    new_bundle = load_bundle(bundle_path)
    assert new_bundle.version.endswith("_auto")
    assert new_bundle.version != old_version

    # Policy file should exist and have thresholds.
    policy_path = Path("backend/policies/decision_engine_policy.json")
    assert policy_path.is_file()
    assert isinstance(result["policy_thresholds"], dict)
    assert result["policy_thresholds"]

