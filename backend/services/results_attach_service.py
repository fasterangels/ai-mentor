"""Attach final result to a snapshot (analysis run) and resolve market outcomes."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict, List

from sqlalchemy.ext.asyncio import AsyncSession

from evaluation.market_resolver import (
    FinalResult,
    MarketOutcomes,
    SnapshotPicks,
    resolve_markets,
)
from models.analysis_run import AnalysisRun
from models.prediction import Prediction
from models.snapshot_resolution import SnapshotResolution
from repositories.analysis_run_repo import AnalysisRunRepository
from repositories.prediction_repo import PredictionRepository
from repositories.snapshot_resolution_repo import SnapshotResolutionRepository


# Market name in DB -> our API key
_MARKET_TO_KEY = {
    "1X2": "one_x_two",
    "OU25": "over_under_25",
    "OU_2.5": "over_under_25",
    "GGNG": "gg_ng",
    "BTTS": "gg_ng",
}

# Valid pick values per market for building SnapshotPicks
_1X2_PICKS = ("HOME", "DRAW", "AWAY", "NO_BET", "NO_PREDICTION")
_OU_PICKS = ("OVER", "UNDER", "NO_BET", "NO_PREDICTION")
_GGNG_PICKS = ("GG", "NG", "NO_BET", "NO_PREDICTION")


def _normalize_pick_for_resolver(decision: str) -> str:
    """Map NO_BET to NO_PREDICTION for resolver."""
    if decision in ("NO_BET", "NO_PREDICTION"):
        return "NO_PREDICTION"
    return decision


def _picks_from_predictions(predictions: List[Prediction]) -> SnapshotPicks:
    """Build SnapshotPicks from prediction rows (one per market)."""
    by_key: Dict[str, str] = {}
    for p in predictions:
        key = _MARKET_TO_KEY.get(p.market.upper() if p.market else "")
        if not key:
            continue
        # Use pick if set, else decision
        raw = (p.pick or p.decision or "NO_PREDICTION").upper()
        if key == "one_x_two" and raw in _1X2_PICKS:
            by_key[key] = _normalize_pick_for_resolver(raw)
        elif key == "over_under_25" and raw in _OU_PICKS:
            by_key[key] = _normalize_pick_for_resolver(raw)
        elif key == "gg_ng" and raw in _GGNG_PICKS:
            by_key[key] = _normalize_pick_for_resolver(raw)

    return SnapshotPicks(
        one_x_two=by_key.get("one_x_two", "NO_PREDICTION"),
        over_under_25=by_key.get("over_under_25", "NO_PREDICTION"),
        gg_ng=by_key.get("gg_ng", "NO_PREDICTION"),
    )


def _reason_codes_from_predictions(predictions: List[Prediction]) -> Dict[str, List[str]]:
    """
    Build reason_codes_by_market from predictions' reasons_json. Uses reason strings as codes.
    Null-safe: missing, null, or empty reasons_json yields empty lists; never raises.
    """
    out: Dict[str, List[str]] = {
        "one_x_two": [],
        "over_under_25": [],
        "gg_ng": [],
    }
    for p in predictions:
        key = _MARKET_TO_KEY.get((p.market or "").upper())
        if not key or key not in out:
            continue
        reasons: List[str] = []
        try:
            raw = getattr(p, "reasons_json", None)
            if raw is None or (isinstance(raw, str) and not raw.strip()):
                reasons = []
            else:
                parsed = json.loads(raw) if isinstance(raw, str) else raw
                if isinstance(parsed, list):
                    reasons = [str(r) for r in parsed[:20]]
        except (json.JSONDecodeError, TypeError, AttributeError):
            reasons = []
        out[key] = reasons
    return out


def _market_outcomes_to_dict(mo: MarketOutcomes) -> Dict[str, str]:
    return {
        "one_x_two": mo.one_x_two,
        "over_under_25": mo.over_under_25,
        "gg_ng": mo.gg_ng,
    }


async def attach_result(
    session: AsyncSession,
    snapshot_id: str,
    home_goals: int,
    away_goals: int,
    status: str = "FINAL",
) -> Dict[str, Any]:
    """
    Load snapshot (analysis run), write final_result, compute market_outcomes, persist.

    snapshot_id is analysis_run_id (as string).
    Returns snapshot_id, market_outcomes, final_result.
    """
    try:
        run_id = int(snapshot_id)
    except (ValueError, TypeError):
        raise ValueError("snapshot_id must be an integer (analysis_run_id)")

    run_repo = AnalysisRunRepository(session)
    pred_repo = PredictionRepository(session)
    resolution_repo = SnapshotResolutionRepository(session)

    run: AnalysisRun | None = await run_repo.get_by_id(run_id)
    if run is None:
        raise ValueError(f"Snapshot not found: snapshot_id={snapshot_id}")

    predictions = await pred_repo.list_by_analysis_run(run_id)
    if not predictions:
        raise ValueError(
            f"No predictions found for snapshot (analysis_run_id={snapshot_id})"
        )

    picks = _picks_from_predictions(predictions)
    final = FinalResult(
        home_goals=home_goals,
        away_goals=away_goals,
        status=status or "FINAL",
    )
    market_outcomes = resolve_markets(picks, final)
    reason_codes = _reason_codes_from_predictions(predictions)

    resolved_at = datetime.now(timezone.utc)

    existing = await resolution_repo.get_by_analysis_run_id(run_id)
    if existing:
        existing.home_goals = home_goals
        existing.away_goals = away_goals
        existing.status = final.status
        existing.resolved_at_utc = resolved_at
        existing.market_outcomes_json = json.dumps(_market_outcomes_to_dict(market_outcomes))
        existing.reason_codes_by_market_json = json.dumps(reason_codes)
        session.add(existing)
    else:
        resolution = SnapshotResolution(
            analysis_run_id=run_id,
            home_goals=home_goals,
            away_goals=away_goals,
            status=final.status,
            resolved_at_utc=resolved_at,
            market_outcomes_json=json.dumps(_market_outcomes_to_dict(market_outcomes)),
            reason_codes_by_market_json=json.dumps(reason_codes),
        )
        await resolution_repo.create(resolution)

    final_result = {
        "home_goals": home_goals,
        "away_goals": away_goals,
        "status": final.status,
        "resolved_at": resolved_at.isoformat(),
    }
    return {
        "snapshot_id": snapshot_id,
        "market_outcomes": _market_outcomes_to_dict(market_outcomes),
        "final_result": final_result,
    }
