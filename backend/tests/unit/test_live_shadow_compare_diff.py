"""
Unit tests for live shadow compare diff engine: identity parity, odds presence, odds value drift, schema drift, alerts.
"""

from __future__ import annotations

import sys
from pathlib import Path

_backend = Path(__file__).resolve().parent.parent.parent
if str(_backend) not in sys.path:
    sys.path.insert(0, str(_backend))

import pytest

from ingestion.connectors.platform_base import IngestedMatchData
from reports.live_shadow_compare import (
    DEFAULT_POLICY,
    build_snapshot_list,
    compare,
    ingested_to_dict,
)


def _make_data(match_id: str, home: str = "Home", away: str = "Away", kickoff: str = "2025-10-01T18:00:00+00:00", odds: dict | None = None) -> IngestedMatchData:
    return IngestedMatchData(
        match_id=match_id,
        home_team=home,
        away_team=away,
        competition="League",
        kickoff_utc=kickoff,
        odds_1x2=odds or {"home": 2.0, "draw": 3.0, "away": 3.5},
        status="scheduled",
    )


def test_ingested_to_dict() -> None:
    d = _make_data("m1")
    out = ingested_to_dict(d)
    assert out["match_id"] == "m1"
    assert out["odds_1x2"]["home"] == 2.0


def test_build_snapshot_list_deterministic_order() -> None:
    items = [("m2", _make_data("m2")), ("m1", _make_data("m1"))]
    snap = build_snapshot_list(items)
    assert [s["match_id"] for s in snap] == ["m1", "m2"]


def test_compare_identity_parity_match() -> None:
    live = [{"match_id": "m1", "data": ingested_to_dict(_make_data("m1", "A", "B"))}]
    rec = [{"match_id": "m1", "data": ingested_to_dict(_make_data("m1", "A", "B"))}]
    report = compare(live, rec)
    assert report["identity_parity"]["m1"]["parity"] is True
    assert report["summary"]["identity_mismatch_count"] == 0


def test_compare_identity_parity_mismatch() -> None:
    live = [{"match_id": "m1", "data": ingested_to_dict(_make_data("m1", "A", "B"))}]
    rec = [{"match_id": "m1", "data": ingested_to_dict(_make_data("m1", "A", "C"))}]
    report = compare(live, rec)
    assert report["identity_parity"]["m1"]["parity"] is False
    assert report["summary"]["identity_mismatch_count"] == 1


def test_compare_odds_value_drift() -> None:
    live = [{"match_id": "m1", "data": ingested_to_dict(_make_data("m1", odds={"home": 2.5, "draw": 3.0, "away": 3.5}))}]
    rec = [{"match_id": "m1", "data": ingested_to_dict(_make_data("m1", odds={"home": 2.0, "draw": 3.0, "away": 3.5}))}]
    report = compare(live, rec)
    assert "m1" in report["odds_value_drift"]
    assert report["odds_value_drift"]["m1"]["deltas"]["home"]["abs_delta"] == 0.5
    assert report["summary"]["odds_outlier_count"] >= 1


def test_compare_schema_drift_missing_field() -> None:
    live = [{"match_id": "m1", "data": ingested_to_dict(_make_data("m1"))}]
    rec = [{"match_id": "m1", "data": {**ingested_to_dict(_make_data("m1")), "odds_1x2": None}}]
    rec[0]["data"].pop("odds_1x2")
    report = compare(live, rec)
    assert report["schema_drift"]["m1"]["missing_in_recorded"] == ["odds_1x2"]
    assert report["summary"]["schema_drift_count"] == 1


def test_compare_alerts_when_threshold_exceeded() -> None:
    policy = {**DEFAULT_POLICY, "max_identity_mismatch_count": 0}
    live = [{"match_id": "m1", "data": ingested_to_dict(_make_data("m1", "A", "B"))}]
    rec = [{"match_id": "m1", "data": ingested_to_dict(_make_data("m1", "X", "Y"))}]
    report = compare(live, rec, policy=policy)
    codes = [a["code"] for a in report["alerts"]]
    assert "LIVE_SHADOW_IDENTITY_MISMATCH" in codes


def test_compare_no_alerts_under_threshold() -> None:
    live = [{"match_id": "m1", "data": ingested_to_dict(_make_data("m1"))}]
    rec = [{"match_id": "m1", "data": ingested_to_dict(_make_data("m1"))}]
    report = compare(live, rec)
    assert report["summary"]["identity_mismatch_count"] == 0
    assert report["summary"]["schema_drift_count"] == 0
    assert len(report["alerts"]) == 0
