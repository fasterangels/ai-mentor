"""Unit tests for injury shadow feature module (pure) and INJ_* reason codes."""

from __future__ import annotations

from analyzer.v2.reason_codes import (
    ALL_REASON_CODES,
    INJ_COVERAGE_LOW,
    INJ_HIGH_UNCERTAINTY,
    INJ_KEY_PLAYER_OUT,
    INJ_MULTIPLE_OUT,
    INJ_CONFLICT_PRESENT,
)
from injury_shadow.features import compute_injury_shadow_features


def test_counts_correct() -> None:
    """Counts for out, questionable, suspended, unknown are correct."""
    resolutions = [
        {"team_ref": "T1", "player_ref": "P1", "resolved_status": "OUT", "resolution_confidence": 0.9, "resolution_method": "LATEST_WINS", "resolution_id": "r1"},
        {"team_ref": "T1", "player_ref": "P2", "resolved_status": "OUT", "resolution_confidence": 0.8, "resolution_method": "LATEST_WINS", "resolution_id": "r2"},
        {"team_ref": "T1", "player_ref": "P3", "resolved_status": "QUESTIONABLE", "resolution_confidence": 0.6, "resolution_method": "LATEST_WINS", "resolution_id": "r3"},
        {"team_ref": "T1", "player_ref": None, "resolved_status": "SUSPENDED", "resolution_confidence": 1.0, "resolution_method": "LATEST_WINS", "resolution_id": "r4"},
        {"team_ref": "T1", "player_ref": "P5", "resolved_status": "UNKNOWN", "resolution_confidence": 0.5, "resolution_method": "LATEST_WINS", "resolution_id": "r5"},
        {"team_ref": "T1", "player_ref": "P6", "resolved_status": "AVAILABLE", "resolution_confidence": 0.95, "resolution_method": "LATEST_WINS", "resolution_id": "r6"},
    ]
    out = compute_injury_shadow_features(resolutions)
    assert out["out_count"] == 2
    assert out["questionable_count"] == 1
    assert out["suspended_count"] == 1
    assert out["unknown_count"] == 1


def test_uncertainty_index_rounding() -> None:
    """uncertainty_index = round(sum(weight * (1 - conf)), 4)."""
    resolutions = [
        {"team_ref": "T", "player_ref": "P1", "resolved_status": "OUT", "resolution_confidence": 0.9, "resolution_method": "L", "resolution_id": "1"},
        {"team_ref": "T", "player_ref": "P2", "resolved_status": "QUESTIONABLE", "resolution_confidence": 0.6, "resolution_method": "L", "resolution_id": "2"},
    ]
    out = compute_injury_shadow_features(resolutions)
    assert out["uncertainty_index"] == 0.3

    resolutions2 = [
        {"team_ref": "T", "player_ref": "P1", "resolved_status": "OUT", "resolution_confidence": 0.8889, "resolution_method": "L", "resolution_id": "1"},
        {"team_ref": "T", "player_ref": "P2", "resolved_status": "QUESTIONABLE", "resolution_confidence": 0.7778, "resolution_method": "L", "resolution_id": "2"},
    ]
    out2 = compute_injury_shadow_features(resolutions2)
    assert out2["uncertainty_index"] == round(1.0 * (1 - 0.8889) + 0.5 * (1 - 0.7778), 4)


def test_key_items_ordering_deterministic() -> None:
    """key_items sorted by weight desc, then confidence asc, then player_ref, then resolution_id."""
    resolutions = [
        {"team_ref": "T", "player_ref": "B", "resolved_status": "OUT", "resolution_confidence": 0.8, "resolution_method": "L", "resolution_id": "2"},
        {"team_ref": "T", "player_ref": "A", "resolved_status": "OUT", "resolution_confidence": 0.8, "resolution_method": "L", "resolution_id": "1"},
        {"team_ref": "T", "player_ref": "C", "resolved_status": "QUESTIONABLE", "resolution_confidence": 0.5, "resolution_method": "L", "resolution_id": "3"},
    ]
    out = compute_injury_shadow_features(resolutions, top_k=3)
    assert len(out["key_items"]) == 3
    assert out["key_items"][0]["player_ref"] == "A"
    assert out["key_items"][0]["resolution_id"] == "1"
    assert out["key_items"][1]["player_ref"] == "B"
    assert out["key_items"][2]["resolved_status"] == "QUESTIONABLE"


def test_key_items_lower_confidence_first() -> None:
    """Among same weight, lower resolution_confidence comes first (risk highlight)."""
    resolutions = [
        {"team_ref": "T", "player_ref": "P1", "resolved_status": "OUT", "resolution_confidence": 0.9, "resolution_method": "L", "resolution_id": "1"},
        {"team_ref": "T", "player_ref": "P2", "resolved_status": "OUT", "resolution_confidence": 0.5, "resolution_method": "L", "resolution_id": "2"},
    ]
    out = compute_injury_shadow_features(resolutions, top_k=2)
    assert out["key_items"][0]["resolution_confidence"] == 0.5
    assert out["key_items"][1]["resolution_confidence"] == 0.9


def test_key_items_top_k() -> None:
    """key_items limited to top_k."""
    resolutions = [
        {"team_ref": "T", "player_ref": f"P{i}", "resolved_status": "OUT", "resolution_confidence": 0.8, "resolution_method": "L", "resolution_id": str(i)}
        for i in range(10)
    ]
    out = compute_injury_shadow_features(resolutions, top_k=5)
    assert len(out["key_items"]) == 5


def test_empty_resolutions() -> None:
    """Empty list yields zeros and empty key_items."""
    out = compute_injury_shadow_features([])
    assert out["out_count"] == 0
    assert out["questionable_count"] == 0
    assert out["suspended_count"] == 0
    assert out["unknown_count"] == 0
    assert out["uncertainty_index"] == 0.0
    assert out["key_items"] == []


def test_reason_codes_in_registry() -> None:
    """INJ_* reason codes exist in ALL_REASON_CODES."""
    assert INJ_MULTIPLE_OUT in ALL_REASON_CODES
    assert INJ_HIGH_UNCERTAINTY in ALL_REASON_CODES
    assert INJ_CONFLICT_PRESENT in ALL_REASON_CODES
    assert INJ_COVERAGE_LOW in ALL_REASON_CODES
    assert INJ_KEY_PLAYER_OUT in ALL_REASON_CODES


def test_reason_codes_values() -> None:
    """INJ_* constants have expected string values."""
    assert INJ_MULTIPLE_OUT == "INJ_MULTIPLE_OUT"
    assert INJ_HIGH_UNCERTAINTY == "INJ_HIGH_UNCERTAINTY"
    assert INJ_CONFLICT_PRESENT == "INJ_CONFLICT_PRESENT"
    assert INJ_COVERAGE_LOW == "INJ_COVERAGE_LOW"
    assert INJ_KEY_PLAYER_OUT == "INJ_KEY_PLAYER_OUT"
