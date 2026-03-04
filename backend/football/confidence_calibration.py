"""Confidence calibration: calibrate model probabilities using historical outcomes."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple

# Overridable by tests (e.g. tmp_path)
DATA_PATH: Path = Path(__file__).resolve().parent.parent / "runtime" / "historical_matches.jsonl"


@dataclass
class CalibrationBin:
    lower: float
    upper: float
    accuracy: float
    count: int


def load_records() -> List[dict]:
    if not DATA_PATH.exists():
        return []
    rows = []
    try:
        with open(DATA_PATH, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                r = json.loads(line)
                if r.get("result") is not None:
                    rows.append(r)
    except (OSError, json.JSONDecodeError):
        return []
    return rows


def get_predicted_class(r: dict) -> Tuple[str, float]:
    return max(
        [
            ("home", r["predicted_home"]),
            ("draw", r["predicted_draw"]),
            ("away", r["predicted_away"]),
        ],
        key=lambda x: x[1],
    )


def build_calibration_bins(records: List[dict], bins: int = 10) -> List[CalibrationBin]:
    size = 1.0 / bins
    result = []
    for i in range(bins):
        lower = i * size
        upper = lower + size
        subset = []
        for r in records:
            label, prob = get_predicted_class(r)
            if lower <= prob < upper:
                subset.append((label, r["result"]))
        correct = sum(1 for p, res in subset if p == res)
        accuracy = correct / len(subset) if subset else 0.0
        result.append(CalibrationBin(lower=lower, upper=upper, accuracy=accuracy, count=len(subset)))
    return result


def calibrate_probability(prob: float, bins: List[CalibrationBin]) -> float:
    for b in bins:
        if b.lower <= prob < b.upper and b.count > 0:
            return b.accuracy
    return prob


def apply_calibration(prediction: Dict[str, float], bins: List[CalibrationBin]) -> Dict[str, float]:
    h = calibrate_probability(prediction["home_prob"], bins)
    d = calibrate_probability(prediction["draw_prob"], bins)
    a = calibrate_probability(prediction["away_prob"], bins)
    s = h + d + a
    if s == 0:
        return prediction
    return {
        "home_prob": h / s,
        "draw_prob": d / s,
        "away_prob": a / s,
    }
