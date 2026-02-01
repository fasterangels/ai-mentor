"""Evaluator: compare predictions with final match results and persist outcomes."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from models.prediction import Prediction
from models.prediction_outcome import PredictionOutcome
from repositories.prediction_repo import PredictionRepository
from repositories.prediction_outcome_repo import PredictionOutcomeRepository

from .types import (
    EvaluationResult,
    OUTCOME_HIT,
    OUTCOME_MISS,
    OUTCOME_NA,
)


def _compute_final_result_1x2(home_score: int, away_score: int) -> str:
    """Compute 1X2 result from final scores. Deterministic."""
    if home_score > away_score:
        return "1"  # HOME
    if home_score < away_score:
        return "2"  # AWAY
    return "X"  # DRAW


def _compute_final_result_ou25(home_score: int, away_score: int) -> str:
    """Compute Over/Under 2.5 result. OVER if total >= 3, else UNDER."""
    total = home_score + away_score
    return "OVER" if total >= 3 else "UNDER"


def _compute_final_result_ggng(home_score: int, away_score: int) -> str:
    """Compute GG/NG result. GG if both teams scored."""
    if home_score >= 1 and away_score >= 1:
        return "GG"
    return "NG"


def _decision_to_1x2(decision: str) -> Optional[str]:
    """Map analyzer decision to 1X2 code for comparison."""
    if decision == "HOME":
        return "1"
    if decision == "AWAY":
        return "2"
    if decision == "DRAW":
        return "X"
    return None  # NO_BET or unknown


def _evaluate_market(
    market: str,
    decision: str,
    actual_1x2: str,
    actual_ou25: str,
    actual_ggng: str,
) -> str:
    """Return HIT, MISS, or N/A for one market."""
    if decision == "NO_BET":
        return OUTCOME_NA

    if market == "1X2":
        expected = _decision_to_1x2(decision)
        if expected is None:
            return OUTCOME_NA
        return OUTCOME_HIT if actual_1x2 == expected else OUTCOME_MISS

    if market == "OU25":
        if decision not in ("OVER", "UNDER"):
            return OUTCOME_NA
        return OUTCOME_HIT if decision == actual_ou25 else OUTCOME_MISS

    if market == "GGNG":
        if decision not in ("GG", "NG"):
            return OUTCOME_NA
        return OUTCOME_HIT if decision == actual_ggng else OUTCOME_MISS

    return OUTCOME_NA


async def evaluate_prediction(
    session: AsyncSession,
    prediction_id: int,
    final_home_score: int,
    final_away_score: int,
    evaluated_at_utc: datetime,
) -> EvaluationResult:
    """Evaluate a single prediction against final match results.

    Steps:
    1. Load Prediction by ID (raise if not found).
    2. Compute market outcomes deterministically (1X2, OU25, GGNG).
    3. If decision was NO_BET, return PENDING with N/A for that market.
    4. Create PredictionOutcome row with full match results and hit_bool.
    5. Return structured EvaluationResult.
    """
    prediction_repo = PredictionRepository(session)
    outcome_repo = PredictionOutcomeRepository(session)

    prediction: Optional[Prediction] = await prediction_repo.get_by_id(
        Prediction, prediction_id
    )
    if prediction is None:
        raise ValueError(f"Prediction not found: prediction_id={prediction_id}")

    # Ensure evaluated_at_utc is timezone-aware
    if evaluated_at_utc.tzinfo is None:
        evaluated_at_utc = evaluated_at_utc.replace(tzinfo=timezone.utc)

    # Compute actual results for all markets (deterministic)
    actual_1x2 = _compute_final_result_1x2(final_home_score, final_away_score)
    actual_ou25 = _compute_final_result_ou25(final_home_score, final_away_score)
    actual_ggng = _compute_final_result_ggng(final_home_score, final_away_score)

    # Evaluate this prediction's market only (one Prediction row = one market)
    market = prediction.market
    decision = prediction.decision

    outcome_str = _evaluate_market(
        market, decision, actual_1x2, actual_ou25, actual_ggng
    )

    # Build market_results for response (this prediction is single-market)
    market_results = {
        "1X2": OUTCOME_NA,
        "OU25": OUTCOME_NA,
        "GGNG": OUTCOME_NA,
    }
    market_results[market] = outcome_str

    # If NO_BET / N/A, return PENDING and do not persist outcome row
    if outcome_str == OUTCOME_NA:
        return EvaluationResult(status="PENDING", market_results=market_results)

    # Persist PredictionOutcome
    hit_bool = outcome_str == OUTCOME_HIT
    outcome_row = PredictionOutcome(
        prediction_id=prediction_id,
        match_id=prediction.match_id,
        evaluated_at_utc=evaluated_at_utc,
        final_home_score=final_home_score,
        final_away_score=final_away_score,
        final_result_1x2=actual_1x2,
        final_ou25=actual_ou25,
        final_ggng=actual_ggng,
        hit_bool=hit_bool,
    )
    await outcome_repo.create(outcome_row)

    return EvaluationResult(status="EVALUATED", market_results=market_results)
