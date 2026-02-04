"""Load/save policy; default policy; checksums."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from policy.policy_model import MarketPolicy, Policy, PolicyVersion, ReasonPolicy


def _json_default(o: Any) -> Any:
    if isinstance(o, datetime):
        return o.isoformat()
    raise TypeError(f"Object of type {type(o).__name__} is not JSON serializable")


def stable_json_dumps(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), default=_json_default)


def checksum_report(data: dict[str, Any] | str) -> str:
    if isinstance(data, dict):
        data = stable_json_dumps(data)
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def default_policy() -> Policy:
    return Policy(
        meta=PolicyVersion(
            version="v0",
            created_at_utc=datetime(2025, 1, 1, 0, 0, 0),
            notes="Default in-code policy",
        ),
        markets={
            "one_x_two": MarketPolicy(min_confidence=0.62),
            "over_under_25": MarketPolicy(min_confidence=0.62),
            "gg_ng": MarketPolicy(min_confidence=0.62),
        },
        reasons={},
    )


def _default_policies_dir() -> Path:
    return Path(__file__).resolve().parent.parent / "policies"


def default_policy_path() -> Path:
    return _default_policies_dir() / "policy_v0.json"


def load_policy(path: str | Path) -> Policy:
    path = Path(path)
    text = path.read_text(encoding="utf-8")
    return Policy.model_validate(json.loads(text))


def save_policy(policy: Policy, path: str | Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = policy.model_dump(mode="json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, sort_keys=True, indent=2, default=_json_default)
