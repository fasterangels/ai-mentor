"""
Unit tests for G4 Part A: age bands, staleness model, and core aggregation.
"""

from __future__ import annotations

from evaluation.staleness_metrics import (
    StalenessReport,
    StalenessRow,
    band_for_age_ms,
    compute_staleness_metrics,
)
from evaluation.staleness_metrics.age_bands import (
    BAND_LABELS,
    BAND_UPPER_BOUNDS_MS,
    DAYS_MS,
    HOURS_MS,
    MINUTES_MS,
)


class TestBandForAgeMs:
    """Band assignment and boundary cases."""

    def test_zero_returns_0_30m(self) -> None:
        assert band_for_age_ms(0) == "0-30m"

    def test_negative_treated_as_zero(self) -> None:
        assert band_for_age_ms(-1) == "0-30m"

    def test_just_under_30m(self) -> None:
        assert band_for_age_ms(30 * MINUTES_MS - 1) == "0-30m"

    def test_30m_exact_in_30_120m(self) -> None:
        assert band_for_age_ms(30 * MINUTES_MS) == "30-120m"

    def test_120m_exact_in_2_6h(self) -> None:
        assert band_for_age_ms(120 * MINUTES_MS) == "2-6h"

    def test_6h_exact_in_6_24h(self) -> None:
        assert band_for_age_ms(6 * HOURS_MS) == "6-24h"

    def test_24h_exact_in_1_3d(self) -> None:
        assert band_for_age_ms(24 * HOURS_MS) == "1-3d"

    def test_3d_exact_in_3_7d(self) -> None:
        assert band_for_age_ms(3 * DAYS_MS) == "3-7d"

    def test_7d_exact_in_7d_plus(self) -> None:
        assert band_for_age_ms(7 * DAYS_MS) == "7d+"

    def test_large_age_7d_plus(self) -> None:
        assert band_for_age_ms(30 * DAYS_MS) == "7d+"

    def test_labels_match_bounds_count(self) -> None:
        assert len(BAND_LABELS) == len(BAND_UPPER_BOUNDS_MS)


class TestStalenessRowAndReport:
    """StalenessRow / StalenessReport and sort key."""

    def test_sort_key_order(self) -> None:
        a = StalenessRow("gg_ng", "B", "7d+", 1, 1, 0, 0.6)
        b = StalenessRow("one_x_two", "A", "0-30m", 1, 1, 0, 0.65)
        assert a.sort_key() < b.sort_key()  # gg_ng < one_x_two

    def test_to_dict_has_accuracy_neutral_rate(self) -> None:
        row = StalenessRow("one_x_two", "R1", "0-30m", 10, 7, 1, 0.62)
        d = row.to_dict()
        assert d["market"] == "one_x_two"
        assert d["total"] == 10
        assert d["correct"] == 7
        assert d["neutral"] == 1
        # 10 total, 7 correct, 1 neutral -> 2 failure; accuracy = 7/(7+2) = 7/9
        assert d["accuracy"] == round(7 / 9, 4)
        assert d["neutral_rate"] == 0.1


class TestComputeStalenessMetrics:
    """Aggregation correctness and deterministic ordering."""

    def test_empty_records_returns_empty_rows(self) -> None:
        def resolver(r: dict) -> int | None:
            return 0
        report = compute_staleness_metrics([], resolver)
        assert report.rows == []
        assert report.computed_at_utc

    def test_one_record_one_reason(self) -> None:
        records = [
            {
                "market_outcomes": {"one_x_two": "SUCCESS"},
                "reason_codes_by_market": {"one_x_two": ["R1"]},
                "market_to_confidence": {"one_x_two": 0.65},
            },
        ]
        def resolver(r: dict) -> int | None:
            return 0
        report = compute_staleness_metrics(records, resolver)
        assert len(report.rows) == 1
        row = report.rows[0]
        assert row.market == "one_x_two"
        assert row.reason_code == "R1"
        assert row.age_band == "0-30m"
        assert row.total == 1
        assert row.correct == 1
        assert row.neutral == 0
        assert row.avg_confidence == 0.65

    def test_resolver_none_uses_0_30m(self) -> None:
        records = [
            {
                "market_outcomes": {"over_under_25": "FAILURE"},
                "reason_codes_by_market": {"over_under_25": ["XG"]},
                "market_to_confidence": {},
            },
        ]
        def resolver(r: dict) -> int | None:
            return None
        report = compute_staleness_metrics(records, resolver)
        assert len(report.rows) == 1
        assert report.rows[0].age_band == "0-30m"

    def test_aggregate_correct_and_failure(self) -> None:
        records = [
            {
                "market_outcomes": {"one_x_two": "SUCCESS"},
                "reason_codes_by_market": {"one_x_two": ["R1"]},
                "market_to_confidence": {},
            },
            {
                "market_outcomes": {"one_x_two": "FAILURE"},
                "reason_codes_by_market": {"one_x_two": ["R1"]},
                "market_to_confidence": {},
            },
        ]
        def resolver(r: dict) -> int | None:
            return 0
        report = compute_staleness_metrics(records, resolver)
        assert len(report.rows) == 1
        assert report.rows[0].total == 2
        assert report.rows[0].correct == 1
        assert report.rows[0].to_dict()["accuracy"] == 0.5

    def test_deterministic_ordering(self) -> None:
        records = [
            {
                "market_outcomes": {"gg_ng": "SUCCESS"},
                "reason_codes_by_market": {"gg_ng": ["B"]},
                "market_to_confidence": {},
            },
            {
                "market_outcomes": {"one_x_two": "SUCCESS"},
                "reason_codes_by_market": {"one_x_two": ["A"]},
                "market_to_confidence": {},
            },
        ]
        def resolver(r: dict) -> int | None:
            return 0
        report = compute_staleness_metrics(records, resolver)
        assert len(report.rows) == 2
        assert report.rows[0].market == "gg_ng"
        assert report.rows[1].market == "one_x_two"
        report2 = compute_staleness_metrics(records[::-1], resolver)
        assert [r.market for r in report2.rows] == [r.market for r in report.rows]

    def test_age_band_split(self) -> None:
        """Different resolver results produce different bands."""
        records = [
            {
                "market_outcomes": {"one_x_two": "SUCCESS"},
                "reason_codes_by_market": {"one_x_two": ["R1"]},
                "market_to_confidence": {},
                "_age_ms": 0,
            },
            {
                "market_outcomes": {"one_x_two": "FAILURE"},
                "reason_codes_by_market": {"one_x_two": ["R1"]},
                "market_to_confidence": {},
                "_age_ms": 8 * DAYS_MS,
            },
        ]
        def resolver(r: dict) -> int | None:
            return r.get("_age_ms")
        report = compute_staleness_metrics(records, resolver)
        assert len(report.rows) == 2  # R1 in 0-30m, R1 in 7d+
        bands = {r.age_band for r in report.rows}
        assert "0-30m" in bands
        assert "7d+" in bands
