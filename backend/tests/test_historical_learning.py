"""
Tests for historical learning: store prediction, update result, compute accuracy.
Uses tmp_path and monkeypatch. Deterministic; no network.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

_backend = Path(__file__).resolve().parent.parent
_repo_root = _backend.parent
for _p in (_backend, _repo_root):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from backend.football import historical_learning


def test_prediction_stored(monkeypatch, tmp_path):
    """Store prediction appends a JSON line with match_id and probs; result is None."""
    path = tmp_path / "historical_matches.jsonl"
    monkeypatch.setattr(historical_learning, "DATA_PATH", path)

    prediction = {"home_prob": 0.5, "draw_prob": 0.3, "away_prob": 0.2}
    historical_learning.store_prediction("M1", prediction)

    assert path.exists()
    lines = path.read_text(encoding="utf-8").strip().split("\n")
    assert len(lines) == 1
    record = json.loads(lines[0])
    assert record["match_id"] == "M1"
    assert record["predicted_home"] == 0.5
    assert record["predicted_draw"] == 0.3
    assert record["predicted_away"] == 0.2
    assert record["result"] is None


def test_result_update_works(monkeypatch, tmp_path):
    """update_match_result sets result for the matching match_id."""
    path = tmp_path / "historical_matches.jsonl"
    monkeypatch.setattr(historical_learning, "DATA_PATH", path)
    path.write_text(
        json.dumps({"match_id": "M1", "predicted_home": 0.4, "predicted_draw": 0.3, "predicted_away": 0.3, "result": None}) + "\n"
        + json.dumps({"match_id": "M2", "predicted_home": 0.6, "predicted_draw": 0.2, "predicted_away": 0.2, "result": None}) + "\n",
        encoding="utf-8",
    )

    historical_learning.update_match_result("M1", "home")

    lines = path.read_text(encoding="utf-8").strip().split("\n")
    r1 = json.loads(lines[0])
    r2 = json.loads(lines[1])
    assert r1["match_id"] == "M1" and r1["result"] == "home"
    assert r2["match_id"] == "M2" and r2["result"] is None


def test_accuracy_calculation_correct(monkeypatch, tmp_path):
    """compute_accuracy returns correct/total for records with result set; max prob is predicted outcome."""
    path = tmp_path / "historical_matches.jsonl"
    monkeypatch.setattr(historical_learning, "DATA_PATH", path)
    path.write_text(
        json.dumps({"match_id": "M1", "predicted_home": 0.5, "predicted_draw": 0.3, "predicted_away": 0.2, "result": "home"}) + "\n"
        + json.dumps({"match_id": "M2", "predicted_home": 0.25, "predicted_draw": 0.25, "predicted_away": 0.5, "result": "draw"}) + "\n"
        + json.dumps({"match_id": "M3", "predicted_home": 0.3, "predicted_draw": 0.4, "predicted_away": 0.3, "result": "draw"}) + "\n"
        + json.dumps({"match_id": "M4", "predicted_home": 0.33, "predicted_draw": 0.34, "predicted_away": 0.33, "result": None}) + "\n",
        encoding="utf-8",
    )

    acc = historical_learning.compute_accuracy()

    assert acc == 2.0 / 3.0
