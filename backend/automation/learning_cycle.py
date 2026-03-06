from __future__ import annotations

from pathlib import Path
from typing import Any, Dict
import json

from backend.policies.fit_decision_engine_policy import (
    FitConfig,
    fit_and_save_policy_from_report,
)
from backend.runtime.decision_bundle import (
    DecisionBundle,
    load_bundle,
    save_bundle,
)


def run_learning_cycle(report_path: str) -> Dict[str, Any]:
    """
    Run automated improvement cycle:
      evaluation report -> policy fitting -> decision bundle update.
    """
    policy_path = "backend/policies/decision_engine_policy.json"
    bundle_path = "backend/runtime/decision_bundle.json"

    cfg = FitConfig(
        objective="precision",
        min_coverage=0.20,
        target_precision=0.70,
    )

    # Fit new policy
    policy = fit_and_save_policy_from_report(
        report_path,
        policy_path,
        cfg,
    )

    # Update bundle version
    bundle = load_bundle(bundle_path)
    new_version = f"{bundle.version}_auto"

    new_bundle = DecisionBundle(
        version=new_version,
        policy_path=policy_path,
        calibrator_path=bundle.calibrator_path,
        reliability_window=bundle.reliability_window,
        meta={"source": "learning_cycle"},
    )

    save_bundle(new_bundle, bundle_path)

    return {
        "new_bundle_version": new_version,
        "policy_thresholds": policy.thresholds,
    }

