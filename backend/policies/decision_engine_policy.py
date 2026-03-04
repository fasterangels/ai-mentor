from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Dict


@dataclass
class DecisionPolicy:
    version: str
    thresholds: Dict[str, float]


DEFAULT_THRESHOLD: float = 0.55


def load_policy(path: str) -> DecisionPolicy:
    """
    Load a decision engine policy from JSON.

    If the file does not exist, returns a default policy with a single
    "default" market threshold.
    """
    p = Path(path)
    if not p.exists():
        return DecisionPolicy(version="default", thresholds={"default": DEFAULT_THRESHOLD})
    data = json.loads(p.read_text())
    return DecisionPolicy(
        version=data.get("version", "v0"),
        thresholds=data.get("thresholds", {"default": DEFAULT_THRESHOLD}),
    )


def save_policy(policy: DecisionPolicy, path: str) -> None:
    """
    Persist a decision engine policy to JSON.
    """
    p = Path(path)
    p.write_text(
        json.dumps(
            {
                "version": policy.version,
                "thresholds": policy.thresholds,
            },
            indent=2,
        )
    )

