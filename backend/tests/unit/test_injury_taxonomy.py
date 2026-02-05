"""Unit tests for injury evaluation taxonomy and compute_injury_evaluation_summary."""

from __future__ import annotations

from evaluation.injury_taxonomy import (
    ALL_INJURY_TAXONOMY_CODES,
    INJ_COVERAGE_MISSING,
    INJ_CONFLICT_UNRESOLVED,
    INJ_FALSE_FIT,
    INJ_FALSE_OUT,
    INJ_PLAYER_MAPPING_FAIL,
    INJ_STALE_DATA_USED,
    compute_injury_evaluation_summary,
)


def test_taxonomy_codes_defined() -> None:
    """All taxonomy codes exist and are in ALL_INJURY_TAXONOMY_CODES."""
    assert INJ_FALSE_OUT == "INJ_FALSE_OUT"
    assert INJ_FALSE_FIT == "INJ_FALSE_FIT"
    assert INJ_CONFLICT_UNRESOLVED == "INJ_CONFLICT_UNRESOLVED"
    assert INJ_STALE_DATA_USED == "INJ_STALE_DATA_USED"
    assert INJ_COVERAGE_MISSING == "INJ_COVERAGE_MISSING"
    assert INJ_PLAYER_MAPPING_FAIL == "INJ_PLAYER_MAPPING_FAIL"
    assert INJ_FALSE_OUT in ALL_INJURY_TAXONOMY_CODES
    assert INJ_COVERAGE_MISSING in ALL_INJURY_TAXONOMY_CODES
    assert len(ALL_INJURY_TAXONOMY_CODES) == 6


def test_compute_injury_evaluation_summary_disabled_empty() -> None:
    """When shadow summary is missing or disabled, return zero/empty structure."""
    out = compute_injury_evaluation_summary({})
    assert out["coverage"]["fixtures_with_injury_shadow"] == 0
    assert out["coverage"]["teams_with_any_resolution"] == 0
    assert out["coverage"]["teams_with_no_resolution"] == 0
    assert out["conflicts"]["conflicts_count"] == 0
    assert out["conflicts"]["conflicts_rate"] == 0.0
    assert out["staleness"]["stale_count"] == 0
    assert out["reasons_emitted_counts"] == {}

    out2 = compute_injury_evaluation_summary({"enabled": False, "resolutions_count": 5})
    assert out2["coverage"]["fixtures_with_injury_shadow"] == 0
    assert out2["reasons_emitted_counts"] == {}


def test_compute_injury_evaluation_summary_deterministic() -> None:
    """Same input => same output (deterministic)."""
    summary = {
        "enabled": True,
        "resolutions_count": 2,
        "team_refs_requested": 2,
        "teams_with_any_resolution": 1,
        "reasons": [{"code": "INJ_COVERAGE_LOW", "text": "x"}, {"code": "INJ_MULTIPLE_OUT", "text": "y"}],
    }
    a = compute_injury_evaluation_summary(summary)
    b = compute_injury_evaluation_summary(summary)
    assert a == b


def test_compute_injury_evaluation_summary_coverage() -> None:
    """Coverage fields reflect team_refs and resolutions."""
    summary = {
        "enabled": True,
        "resolutions_count": 3,
        "team_refs_requested": 2,
        "teams_with_any_resolution": 2,
        "reasons": [],
    }
    out = compute_injury_evaluation_summary(summary)
    assert out["coverage"]["fixtures_with_injury_shadow"] == 1
    assert out["coverage"]["teams_with_any_resolution"] == 2
    assert out["coverage"]["teams_with_no_resolution"] == 0


def test_compute_injury_evaluation_summary_conflict() -> None:
    """Conflict present when INJ_CONFLICT_PRESENT in reasons."""
    summary = {
        "enabled": True,
        "resolutions_count": 1,
        "reasons": [{"code": "INJ_CONFLICT_PRESENT", "text": "conflict"}],
    }
    out = compute_injury_evaluation_summary(summary)
    assert out["conflicts"]["conflicts_count"] == 1
    assert out["conflicts"]["conflicts_rate"] == 1.0


def test_compute_injury_evaluation_summary_reasons_emitted() -> None:
    """reasons_emitted_counts has overall and by_market per code."""
    summary = {
        "enabled": True,
        "resolutions_count": 1,
        "reasons": [
            {"code": "INJ_MULTIPLE_OUT", "text": "a"},
            {"code": "INJ_MULTIPLE_OUT", "text": "b"},
            {"code": "INJ_HIGH_UNCERTAINTY", "text": "c"},
        ],
    }
    out = compute_injury_evaluation_summary(summary)
    counts = out["reasons_emitted_counts"]
    assert counts["INJ_MULTIPLE_OUT"]["overall"] == 2
    assert counts["INJ_HIGH_UNCERTAINTY"]["overall"] == 1
    assert counts["INJ_MULTIPLE_OUT"]["by_market"] == {"1X2": 0, "OU_2.5": 0, "BTTS": 0}
    assert "staleness" in out
    assert out["staleness"]["note"] == "needs claim timestamps linkage"
