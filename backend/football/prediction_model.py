from __future__ import annotations

from dataclasses import dataclass


@dataclass
class PredictionResult:
    home_prob: float
    draw_prob: float
    away_prob: float
    model_score: float


def normalize(a: float, b: float, c: float) -> tuple[float, float, float]:
    s = a + b + c
    if s == 0:
        return 0.33, 0.33, 0.33
    return a / s, b / s, c / s


def build_prediction(features: dict) -> PredictionResult:
    home_intel = features["meta"]["team_intelligence"]["home"]
    away_intel = features["meta"]["team_intelligence"]["away"]
    odds_intel = features["meta"]["odds_intelligence"]

    home_strength = home_intel["form_score"] + home_intel["momentum"] * 0.05
    away_strength = away_intel["form_score"] + away_intel["momentum"] * 0.05

    odds_home = odds_intel["implied_probabilities"].get("home", 0.33)
    odds_draw = odds_intel["implied_probabilities"].get("draw", 0.33)
    odds_away = odds_intel["implied_probabilities"].get("away", 0.33)

    home_raw = home_strength * 0.6 + odds_home * 0.4
    away_raw = away_strength * 0.6 + odds_away * 0.4
    draw_raw = odds_draw

    home, draw, away = normalize(home_raw, draw_raw, away_raw)

    score = abs(home - away)

    return PredictionResult(
        home_prob=home,
        draw_prob=draw,
        away_prob=away,
        model_score=score,
    )
