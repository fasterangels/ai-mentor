# Unit tests for tuner_impact
from __future__ import annotations
import sys
from pathlib import Path
_backend = Path(__file__).resolve().parent.parent.parent
if str(_backend) not in sys.path:
    sys.path.insert(0, str(_backend))
from policy.tuner_impact import MARKETS_ORDER, build_tuner_proposal_diff, build_tuner_impact_by_market

def test_tuner_proposal_diff_deterministic_ordering():
    diffs_a = [("markets.gg_ng.min_confidence", 0.55, 0.57, "r1"), ("markets.one_x_two.min_confidence", 0.50, 0.54, "r2"), ("markets.over_under_25.min_confidence", 0.52, 0.52, "r3")]
    diffs_b = [("markets.over_under_25.min_confidence", 0.52, 0.52, "r3"), ("markets.one_x_two.min_confidence", 0.50, 0.54, "r2"), ("markets.gg_ng.min_confidence", 0.55, 0.57, "r1")]
    out_a = build_tuner_proposal_diff("v1", "v2-tuned", diffs_a, None)
    out_b = build_tuner_proposal_diff("v1", "v2-tuned", diffs_b, None)
    assert out_a["top_changes"] == out_b["top_changes"]
    assert out_a["top_changes"][0]["param_path"] == "markets.one_x_two.min_confidence"

def test_tuner_impact_by_market_stable_ordering_and_rounding():
    eval_report = {"per_market_accuracy": {"one_x_two": {"success_count": 10, "failure_count": 5, "neutral_count": 3}, "over_under_25": {"success_count": 8, "failure_count": 2, "neutral_count": 0}, "gg_ng": {"success_count": 7, "failure_count": 7, "neutral_count": 1}}}
    impact = build_tuner_impact_by_market(eval_report, None)
    assert list(impact.keys()) == list(MARKETS_ORDER)
    assert impact["one_x_two"]["accuracy"] == 0.6667
