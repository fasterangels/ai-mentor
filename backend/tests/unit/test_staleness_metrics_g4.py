"""
Unit tests for G4 staleness metrics: age bands, aggregation, deterministic ordering.
"""

from __future__ import annotations

from evaluation.age_bands import (
    AGE_BAND_LABELS,
    AGE_BAND_THRESHOLDS_MS,
    DAYS_MS,
    HOURS_MS,
    MINUTES_MS,
    assign_age_band,
)
from evaluation.staleness_metrics import (
    StalenessRow,
    _aggregate_staleness_rows,
)


class TestAgeBands:
    """Age band assignment correctness and boundary cases."""

    def test_none_returns_freshest(self) -> None:
        assert assign_age_band(None) == "0-30m"

    def test_negative_returns_freshest(self) -> None:
        assert assign_age_band(-1.0) == "0-30m"

    def test_zero_in_0_30m(self) -> None:
        assert assign_age_band(0) == "0-30m"

    def test_just_under_30m(self) -> None:
        assert assign_age_band(30 * MINUTES_MS - 1) == "0-30m"

    def test_30m_in_30m_2h(self) -> None:
        assert assign_age_band(30 * MINUTES_MS) == "30m-2h"

    def test_2h_in_2h_6h(self) -> None:
        assert assign_age_band(2 * HOURS_MS) == "2h-6h"

    def test_6h_in_6h_24h(self) -> None:
        assert assign_age_band(6 * HOURS_MS) == "6h-24h"

    def test_24h_in_1d_3d(self) -> None:
        assert assign_age_band(24 * HOURS_MS) == "1d-3d"

    def test_3d_in_3d_7d(self) -> None:
        assert assign_age_band(3 * DAYS_MS) == "3d-7d"

    def test_7d_in_7d_plus(self) -> None:
        assert assign_age_band(7 * DAYS_MS) == "7d+"

    def test_large_age_7d_plus(self) -> None:
        assert assign_age_band(30 * DAYS_MS) == "7d+"

    def test_labels_match_thresholds_count(self) -> None:
        assert len(AGE_BAND_LABELS) == len(AGE_BAND_THRESHOLDS_MS)


class TestStalenessAggregation:
    """Aggregation correctness for synthetic dataset and deterministic ordering."""

    def test_aggregate_empty_returns_empty(self) -> None:
        assert _aggregate_staleness_rows([]) == []

    def test_aggregate_one_record_one_reason(self) -> None:
        records = [
            {
                "market_outcomes": {"one_x_two": "SUCCESS"},
                "reason_codes_by_market": {"one_x_two": ["R1"]},
                "market_to_confidence": {"one_x_two": 0.65},
                "age_band": "0-30m",
            },
        ]
        rows = _aggregate_staleness_rows(records)
        assert len(rows) == 1
        assert rows[0].market == "one_x_two"
        assert rows[0].reason_code == "R1"
        assert rows[0].age_band == "0-30m"
        assert rows[0].total == 1
        assert rows[0].correct == 1
        assert rows[0].accuracy == 1.0
        assert rows[0].neutral_rate == 0.0
        assert rows[0].avg_confidence == 0.65

    def test_aggregate_correct_and_failure(self) -> None:
        records = [
            {
                "market_outcomes": {"one_x_two": "SUCCESS"},
                "reason_codes_by_market": {"one_x_two": ["R1"]},
                "market_to_confidence": {},
                "age_band": "0-30m",
            },
            {
                "market_outcomes": {"one_x_two": "FAILURE"},
                "reason_codes_by_market": {"one_x_two": ["R1"]},
                "market_to_confidence": {},
                "age_band": "0-30m",
            },
        ]
        rows = _aggregate_staleness_rows(records)
        assert len(rows) == 1
        assert rows[0].total == 2
        assert rows[0].correct == 1
        assert rows[0].accuracy == 0.5

    def test_aggregate_neutral_rate(self) -> None:
        records = [
            {
                "market_outcomes": {"over_under_25": "SUCCESS"},
                "reason_codes_by_market": {"over_under_25": ["XG"]},
                "market_to_confidence": {},
                "age_band": "30m-2h",
            },
            {
                "market_outcomes": {"over_under_25": "UNRESOLVED"},
                "reason_codes_by_market": {"over_under_25": ["XG"]},
                "market_to_confidence": {},
                "age_band": "30m-2h",
            },
        ]
        rows = _aggregate_staleness_rows(records)
        assert len(rows) == 1
        assert rows[0].total == 2
        assert rows[0].correct == 1
        assert rows[0].neutral_rate == 0.5
        assert rows[0].accuracy == 1.0  # 1 success, 0 failure

    def test_deterministic_ordering(self) -> None:
        records = [
            {
                "market_outcomes": {"gg_ng": "SUCCESS"},
                "reason_codes_by_market": {"gg_ng": ["B"]},
                "market_to_confidence": {},
                "age_band": "7d+",
            },
            {
                "market_outcomes": {"one_x_two": "SUCCESS"},
                "reason_codes_by_market": {"one_x_two": ["A"]},
                "market_to_confidence": {},
                "age_band": "0-30m",
            },
        ]
        rows = _aggregate_staleness_rows(records)
        assert len(rows) == 2
        # Sorted by (market, reason_code, age_band): gg_ng < one_x_two
        assert rows[0].market == "gg_ng"
        assert rows[1].market == "one_x_two"
        rows2 = _aggregate_staleness_rows(records[::-1])
        assert [r.market for r in rows2] == [r.market for r in rows]


class TestStalenessRowToDict:
    """StalenessRow.to_dict() and CSV/JSON export shape."""

    def test_to_dict_roundtrip(self) -> None:
        row = StalenessRow(
            market="one_x_two",
            reason_code="R1",
            age_band="0-30m",
            total=10,
            correct=7,
            accuracy=0.7,
            neutral_rate=0.1,
            avg_confidence=0.62,
        )
        d = row.to_dict()
        assert d["market"] == "one_x_two"
        assert d["reason_code"] == "R1"
        assert d["age_band"] == "0-30m"
        assert d["total"] == 10
        assert d["correct"] == 7
        assert d["accuracy"] == 0.7
        assert d["neutral_rate"] == 0.1
        assert d["avg_confidence"] == 0.62
