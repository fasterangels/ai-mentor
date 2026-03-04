"""Historical learning: store predictions and outcomes for accuracy evaluation."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict

# Overridable by tests (e.g. tmp_path)
DATA_PATH: Path = Path(__file__).resolve().parent.parent / "runtime" / "historical_matches.jsonl"


@dataclass
class HistoricalRecord:
    match_id: str
    predicted_home: float
    predicted_draw: float
    predicted_away: float
    result: str | None


def store_prediction(match_id: str, prediction: Dict[str, Any]) -> None:
    try:
        DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
        record = {
            "match_id": match_id,
            "predicted_home": prediction["home_prob"],
            "predicted_draw": prediction["draw_prob"],
            "predicted_away": prediction["away_prob"],
            "result": None,
        }
        with open(DATA_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")
    except OSError:
        pass


def update_match_result(match_id: str, result: str) -> None:
    if not DATA_PATH.exists():
        return
    try:
        rows = []
        with open(DATA_PATH, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                r = json.loads(line)
                if r["match_id"] == match_id:
                    r["result"] = result
                rows.append(r)
        with open(DATA_PATH, "w", encoding="utf-8") as f:
            for r in rows:
                f.write(json.dumps(r) + "\n")
    except (OSError, json.JSONDecodeError):
        pass


def compute_accuracy() -> float:
    if not DATA_PATH.exists():
        return 0.0
    correct = 0
    total = 0
    try:
        with open(DATA_PATH, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                r = json.loads(line)
                if r.get("result") is None:
                    continue
                total += 1
                predicted = max(
                    [
                        ("home", r["predicted_home"]),
                        ("draw", r["predicted_draw"]),
                        ("away", r["predicted_away"]),
                    ],
                    key=lambda x: x[1],
                )[0]
                if predicted == r["result"]:
                    correct += 1
    except (OSError, json.JSONDecodeError, KeyError):
        return 0.0
    if total == 0:
        return 0.0
    return correct / total
