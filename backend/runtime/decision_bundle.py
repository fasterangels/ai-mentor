from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict
import json


@dataclass
class DecisionBundle:
    version: str
    policy_path: str
    calibrator_path: str
    reliability_window: str  # "30d" | "90d" | "all_time"
    meta: Dict[str, Any]


def load_bundle(path: str) -> DecisionBundle:
    """
    Load a DecisionBundle from JSON, with safe defaults when missing.
    """
    p = Path(path)
    if not p.exists():
        return DecisionBundle(
            version="default",
            policy_path="backend/policies/decision_engine_policy.json",
            calibrator_path="backend/calibration/confidence_calibrator.json",
            reliability_window="90d",
            meta={},
        )
    data = json.loads(p.read_text())
    return DecisionBundle(
        version=data.get("version", "v0"),
        policy_path=data.get("policy_path", "backend/policies/decision_engine_policy.json"),
        calibrator_path=data.get("calibrator_path", "backend/calibration/confidence_calibrator.json"),
        reliability_window=data.get("reliability_window", "90d"),
        meta=data.get("meta", {}),
    )


def save_bundle(bundle: DecisionBundle, path: str) -> None:
    """
    Persist a DecisionBundle to JSON with deterministic key ordering.
    """
    p = Path(path)
    payload = {
        "version": bundle.version,
        "policy_path": bundle.policy_path,
        "calibrator_path": bundle.calibrator_path,
        "reliability_window": bundle.reliability_window,
        "meta": bundle.meta,
    }
    p.write_text(json.dumps(payload, indent=2, sort_keys=True))

