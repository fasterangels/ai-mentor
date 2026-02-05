"""Runtime: get active policy from env or default path."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from policy.policy_model import Policy
from policy.policy_store import default_policy, default_policy_path, load_policy

POLICY_MARKET_KEYS = ("one_x_two", "over_under_25", "gg_ng")


def get_active_policy() -> Policy:
    path_str = os.environ.get("POLICY_PATH")
    path: Optional[Path] = default_policy_path() if not path_str else Path(path_str)
    try:
        if path and path.is_file():
            return load_policy(path)
    except Exception:
        pass
    return default_policy()


def min_confidence_from_policy(policy: Policy) -> float:
    default = default_policy()
    values = [
        policy.markets.get(k, default.markets[k]).min_confidence
        for k in POLICY_MARKET_KEYS
    ]
    return min(values) if values else 0.62
