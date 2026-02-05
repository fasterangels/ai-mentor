"""
Activation tiers (RFC-001): burn_in, limited, expanded with caps, rollout %, and daily cap.
Deterministic rollout selection; daily cap enforced via reports/index (no DB).
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from reports.index_store import load_index

# Hard cap across all tiers (RFC-001)
ACTIVATION_MAX_MATCHES_HARD_CAP = 10

# Allowed tier values
ACTIVATION_TIERS = ("burn_in", "limited", "expanded")


def _tier() -> str:
    """ACTIVATION_TIER env; default burn_in. Off = no activation (handled by gate)."""
    raw = os.environ.get("ACTIVATION_TIER", "burn_in").strip().lower()
    return raw if raw in ACTIVATION_TIERS else "burn_in"


def _rollout_pct() -> float:
    """ACTIVATION_ROLLOUT_PCT 0-100; default 0 (no rollout)."""
    try:
        pct = float(os.environ.get("ACTIVATION_ROLLOUT_PCT", "0"))
    except ValueError:
        return 0.0
    return max(0.0, min(100.0, pct))


def _daily_max_activations() -> int:
    """ACTIVATION_DAILY_MAX_ACTIVATIONS; default 0 (no activations)."""
    try:
        return max(0, int(os.environ.get("ACTIVATION_DAILY_MAX_ACTIVATIONS", "0")))
    except ValueError:
        return 0


def get_tier_config() -> Dict[str, Any]:
    """
    Per-tier: max_matches cap, min_confidence (tier-specific), guardrail strictness.
    expanded still blocks on critical alerts; min_confidence stricter than policy.
    """
    tier = _tier()
    # burn_in: 1-3 matches, 0.85 min conf, strict guardrails (existing)
    # limited: env ACTIVATION_MAX_MATCHES up to hard cap, ACTIVATION_MIN_CONFIDENCE
    # expanded: env ACTIVATION_MAX_MATCHES up to hard cap, min conf 0.80 (stricter than typical policy 0.62)
    configs = {
        "burn_in": {
            "max_matches": (1, 3),  # min, max
            "min_confidence": 0.85,
            "blocks_on_critical_alerts": True,
        },
        "limited": {
            "max_matches": (0, ACTIVATION_MAX_MATCHES_HARD_CAP),
            "min_confidence_env": "ACTIVATION_MIN_CONFIDENCE",
            "min_confidence_default": 0.70,
            "blocks_on_critical_alerts": True,
        },
        "expanded": {
            "max_matches": (0, ACTIVATION_MAX_MATCHES_HARD_CAP),
            "min_confidence_env": "ACTIVATION_MIN_CONFIDENCE",
            "min_confidence_default": 0.80,
            "blocks_on_critical_alerts": True,
        },
    }
    c = configs.get(tier, configs["burn_in"]).copy()
    c["tier"] = tier
    c["rollout_pct"] = _rollout_pct()
    c["daily_max_activations"] = _daily_max_activations()
    return c


def tier_max_matches(tier: Optional[str] = None) -> int:
    """Max matches allowed for tier; env ACTIVATION_MAX_MATCHES capped by tier and hard cap."""
    t = tier or _tier()
    try:
        env_val = int(os.environ.get("ACTIVATION_MAX_MATCHES", "0"))
    except ValueError:
        env_val = 0
    env_val = max(0, min(env_val, ACTIVATION_MAX_MATCHES_HARD_CAP))
    if t == "burn_in":
        from activation.burn_in import BURN_IN_MAX_MATCHES_MAX
        return min(env_val or BURN_IN_MAX_MATCHES_MAX, BURN_IN_MAX_MATCHES_MAX)
    return env_val or 0


def tier_min_confidence(tier: Optional[str] = None) -> float:
    """Min confidence for tier (stricter than policy when set)."""
    t = tier or _tier()
    if t == "burn_in":
        from activation.burn_in import burn_in_min_confidence
        return burn_in_min_confidence()
    try:
        return float(os.environ.get("ACTIVATION_MIN_CONFIDENCE", "0.80"))
    except ValueError:
        return 0.80


def select_rollout_match_ids(match_ids: List[str], rollout_pct: float) -> Set[str]:
    """
    Deterministic: stable sort by match_id, take first N% (by count).
    Returns set of match_ids that are in the rollout set.
    """
    if rollout_pct <= 0:
        return set()
    if rollout_pct >= 100.0:
        return set(match_ids)
    sorted_ids = sorted(match_ids)
    n = len(sorted_ids)
    take = max(0, int(round(n * rollout_pct / 100.0)))
    return set(sorted_ids[:take])


def get_daily_activations_used(index_path: str | Path = "reports/index.json") -> int:
    """
    Count activations today from index (activation_runs and burn_in_ops_runs).
    No DB dependency. Uses created_at_utc date (UTC).
    """
    path = Path(index_path)
    if not path.is_file():
        return 0
    index = load_index(path)
    today = datetime.now(timezone.utc).date().isoformat()

    def is_today(created: Any) -> bool:
        if not created:
            return False
        s = str(created).split("T")[0].split(" ")[0]
        return s == today

    count = 0
    for runs_key, activated_key, count_key in (
        ("activation_runs", "activated", "activated_count"),
        ("burn_in_ops_runs", "activated", "activated_count"),
    ):
        runs = index.get(runs_key) or []
        for r in runs:
            if not is_today(r.get("created_at_utc")):
                continue
            if not r.get(activated_key, False):
                continue
            if count_key and r.get(count_key) is not None:
                count += int(r.get(count_key, 0))
            else:
                count += r.get("matches_count", 1)
    return count


def daily_cap_remaining(index_path: str | Path = "reports/index.json") -> int:
    """Max(0, ACTIVATION_DAILY_MAX_ACTIVATIONS - get_daily_activations_used)."""
    cap = _daily_max_activations()
    if cap <= 0:
        return 0
    used = get_daily_activations_used(index_path)
    return max(0, cap - used)
