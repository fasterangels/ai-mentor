"""
Unit tests for activation tiers (RFC-001): tier rules, rollout selection, daily cap.
No external network.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

_backend = Path(__file__).resolve().parent.parent.parent
if str(_backend) not in sys.path:
    sys.path.insert(0, str(_backend))

import pytest

from activation.tiers import (
    ACTIVATION_MAX_MATCHES_HARD_CAP,
    ACTIVATION_TIERS,
    daily_cap_remaining,
    get_daily_activations_used,
    get_tier_config,
    select_rollout_match_ids,
    tier_max_matches,
    tier_min_confidence,
)


# --- Deterministic rollout selection ---


def test_select_rollout_match_ids_zero_pct_returns_empty() -> None:
    """rollout_pct 0 returns no match_ids in rollout set."""
    assert select_rollout_match_ids(["a", "b", "c"], 0.0) == set()
    assert select_rollout_match_ids([], 0) == set()


def test_select_rollout_match_ids_100_pct_returns_all() -> None:
    """rollout_pct >= 100 returns all match_ids."""
    ids = ["m1", "m2", "m3"]
    assert select_rollout_match_ids(ids, 100.0) == set(ids)
    assert select_rollout_match_ids(ids, 150.0) == set(ids)


def test_select_rollout_match_ids_deterministic_stable_sort() -> None:
    """Selection is deterministic: stable sort by match_id, take first N%."""
    # 4 ids sorted: a, b, c, d. 50% -> take 2.
    ids = ["d", "a", "c", "b"]
    selected = select_rollout_match_ids(ids, 50.0)
    sorted_ids = sorted(ids)
    assert sorted_ids == ["a", "b", "c", "d"]
    take = 2  # 50% of 4
    assert selected == set(sorted_ids[:take])
    assert selected == {"a", "b"}


def test_select_rollout_match_ids_25_pct_one_of_four() -> None:
    """25% of 4 = 1 match in rollout set."""
    ids = ["x", "y", "z", "w"]
    selected = select_rollout_match_ids(ids, 25.0)
    assert len(selected) == 1
    assert "w" in selected  # sorted: w,x,y,z -> first 1 is w


def test_select_rollout_match_ids_33_pct_rounds() -> None:
    """33% of 3: round(n*33/100)=1, so 1 match."""
    ids = ["a", "b", "c"]
    selected = select_rollout_match_ids(ids, 33.0)
    assert len(selected) == 1
    assert "a" in selected


# --- Tier max matches ---


def test_tier_max_matches_burn_in_capped_at_3() -> None:
    """Burn-in tier caps max matches at 3 even if env is higher."""
    with pytest.MonkeyPatch.context() as m:
        m.setenv("ACTIVATION_TIER", "burn_in")
        m.setenv("ACTIVATION_MAX_MATCHES", "10")
        assert tier_max_matches("burn_in") == 3


def test_tier_max_matches_limited_respects_env_and_hard_cap() -> None:
    """Limited tier uses ACTIVATION_MAX_MATCHES up to hard cap."""
    with pytest.MonkeyPatch.context() as m:
        m.setenv("ACTIVATION_TIER", "limited")
        m.setenv("ACTIVATION_MAX_MATCHES", "5")
        assert tier_max_matches("limited") == 5
        m.setenv("ACTIVATION_MAX_MATCHES", "20")
        assert tier_max_matches("limited") == ACTIVATION_MAX_MATCHES_HARD_CAP


def test_tier_max_matches_expanded_same_as_limited() -> None:
    """Expanded tier same cap behavior as limited (env, hard cap)."""
    with pytest.MonkeyPatch.context() as m:
        m.setenv("ACTIVATION_TIER", "expanded")
        m.setenv("ACTIVATION_MAX_MATCHES", "8")
        assert tier_max_matches("expanded") == 8


# --- Tier min confidence ---


def test_tier_min_confidence_burn_in_uses_burn_in_module() -> None:
    """Burn-in tier uses burn_in_min_confidence (can be overridden by env)."""
    with pytest.MonkeyPatch.context() as m:
        m.setenv("ACTIVATION_TIER", "burn_in")
        m.setenv("ACTIVATION_MIN_CONFIDENCE_BURN_IN", "0.88")
        # tier_min_confidence("burn_in") delegates to burn_in.burn_in_min_confidence()
        assert tier_min_confidence("burn_in") == 0.88


def test_tier_min_confidence_limited_uses_env_default_70() -> None:
    """Limited tier uses ACTIVATION_MIN_CONFIDENCE; default 0.80 in code (tiers default)."""
    with pytest.MonkeyPatch.context() as m:
        m.setenv("ACTIVATION_TIER", "limited")
        m.delenv("ACTIVATION_MIN_CONFIDENCE", raising=False)
        # tiers.tier_min_confidence uses env default 0.80
        assert tier_min_confidence("limited") == 0.80
        m.setenv("ACTIVATION_MIN_CONFIDENCE", "0.72")
        assert tier_min_confidence("limited") == 0.72


def test_tier_min_confidence_expanded_stricter() -> None:
    """Expanded tier uses ACTIVATION_MIN_CONFIDENCE (default 0.80)."""
    with pytest.MonkeyPatch.context() as m:
        m.setenv("ACTIVATION_TIER", "expanded")
        m.setenv("ACTIVATION_MIN_CONFIDENCE", "0.82")
        assert tier_min_confidence("expanded") == 0.82


# --- get_tier_config ---


def test_get_tier_config_includes_tier_rollout_daily_cap() -> None:
    """get_tier_config returns tier, rollout_pct, daily_max_activations."""
    with pytest.MonkeyPatch.context() as m:
        m.setenv("ACTIVATION_TIER", "limited")
        m.setenv("ACTIVATION_ROLLOUT_PCT", "25")
        m.setenv("ACTIVATION_DAILY_MAX_ACTIVATIONS", "5")
        c = get_tier_config()
        assert c["tier"] == "limited"
        assert c["rollout_pct"] == 25.0
        assert c["daily_max_activations"] == 5


def test_get_tier_config_burn_in_blocks_critical() -> None:
    """All tiers have blocks_on_critical_alerts True."""
    for tier in ACTIVATION_TIERS:
        with pytest.MonkeyPatch.context() as m:
            m.setenv("ACTIVATION_TIER", tier)
            c = get_tier_config()
            assert c.get("blocks_on_critical_alerts") is True


# --- Daily activations from index ---


def test_get_daily_activations_used_missing_file_returns_zero(tmp_path: Path) -> None:
    """Missing index file returns 0."""
    assert get_daily_activations_used(tmp_path / "nonexistent.json") == 0


def test_get_daily_activations_used_empty_index_returns_zero(tmp_path: Path) -> None:
    """Empty index (no runs) returns 0."""
    index_path = tmp_path / "index.json"
    index_path.write_text(json.dumps({"activation_runs": [], "burn_in_ops_runs": []}))
    assert get_daily_activations_used(str(index_path)) == 0


def test_get_daily_activations_used_counts_today_only(tmp_path: Path) -> None:
    """Counts only runs with created_at_utc today and activated_count."""
    today = datetime.now(timezone.utc).date().isoformat()
    yesterday = "2020-01-01"
    index = {
        "activation_runs": [
            {"created_at_utc": f"{today}T12:00:00Z", "activated": True, "activated_count": 2},
            {"created_at_utc": f"{yesterday}T12:00:00Z", "activated": True, "activated_count": 1},
        ],
        "burn_in_ops_runs": [
            {"created_at_utc": f"{today}T14:00:00Z", "activated": True, "activated_count": 1},
        ],
    }
    index_path = tmp_path / "index.json"
    index_path.write_text(json.dumps(index))
    assert get_daily_activations_used(str(index_path)) == 2 + 1  # 2 from activation_runs today, 1 from burn_in_ops today


def test_get_daily_activations_used_skips_non_activated(tmp_path: Path) -> None:
    """Only entries with activated=True and activated_count count."""
    today = datetime.now(timezone.utc).date().isoformat()
    index = {
        "activation_runs": [
            {"created_at_utc": f"{today}T12:00:00Z", "activated": False, "activated_count": 3},
            {"created_at_utc": f"{today}T13:00:00Z", "activated": True, "activated_count": 2},
        ],
    }
    index_path = tmp_path / "index.json"
    index_path.write_text(json.dumps(index))
    assert get_daily_activations_used(str(index_path)) == 2


# --- daily_cap_remaining ---


def test_daily_cap_remaining_zero_cap_returns_zero() -> None:
    """When ACTIVATION_DAILY_MAX_ACTIVATIONS=0, remaining is 0."""
    with pytest.MonkeyPatch.context() as m:
        m.setenv("ACTIVATION_DAILY_MAX_ACTIVATIONS", "0")
        assert daily_cap_remaining("/nonexistent/index.json") == 0


def test_daily_cap_remaining_no_usage_equals_cap(tmp_path: Path) -> None:
    """When no activations today, remaining = cap."""
    index_path = tmp_path / "index.json"
    index_path.write_text(json.dumps({"activation_runs": [], "burn_in_ops_runs": []}))
    with pytest.MonkeyPatch.context() as m:
        m.setenv("ACTIVATION_DAILY_MAX_ACTIVATIONS", "10")
        assert daily_cap_remaining(str(index_path)) == 10


def test_daily_cap_remaining_after_usage(tmp_path: Path) -> None:
    """Remaining = cap - used (today only)."""
    today = datetime.now(timezone.utc).date().isoformat()
    index = {
        "activation_runs": [
            {"created_at_utc": f"{today}T12:00:00Z", "activated": True, "activated_count": 3},
        ],
        "burn_in_ops_runs": [],
    }
    index_path = tmp_path / "index.json"
    index_path.write_text(json.dumps(index))
    with pytest.MonkeyPatch.context() as m:
        m.setenv("ACTIVATION_DAILY_MAX_ACTIVATIONS", "10")
        assert daily_cap_remaining(str(index_path)) == 7


def test_daily_cap_remaining_never_negative(tmp_path: Path) -> None:
    """Remaining is max(0, cap - used)."""
    today = datetime.now(timezone.utc).date().isoformat()
    index = {
        "activation_runs": [
            {"created_at_utc": f"{today}T12:00:00Z", "activated": True, "activated_count": 20},
        ],
        "burn_in_ops_runs": [],
    }
    index_path = tmp_path / "index.json"
    index_path.write_text(json.dumps(index))
    with pytest.MonkeyPatch.context() as m:
        m.setenv("ACTIVATION_DAILY_MAX_ACTIVATIONS", "5")
        assert daily_cap_remaining(str(index_path)) == 0
