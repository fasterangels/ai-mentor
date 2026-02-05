"""Attach final result to an analysis snapshot: compute market outcomes and persist SnapshotResolution."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict

from sqlalchemy.ext.asyncio import AsyncSession

from models.snapshot_resolution import SnapshotResolution
from repositories.prediction_repo import PredictionRepository
from repositories.snapshot_resolution_repo import SnapshotResolutionRepository

# Analyzer market -> policy/eval market key
MARKET_TO_KEY = {"1X2": "one_x_two", "OU_2.5": "over_under_25", "OU25": "over_under_25", "BTTS": "gg_ng", "GGNG": "gg_ng"}


def _outcome_1x2(pick: str, home: int, away: int) -> str:
    if home > away:
        actual = "HOME"
    elif away > home:
        actual = "AWAY"
    else:
        actual = "DRAW"
    return "SUCCESS" if pick == actual else "FAILURE"


def _outcome_ou25(pick: str, home: int, away: int) -> str:
    total = home + away
    if total > 2.5:
        actual = "OVER"
    else:
        actual = "UNDER"
    return "SUCCESS" if pick == actual else "FAILURE"


def _outcome_ggng(pick: str, home: int, away: int) -> str:
    both_scored = home > 0 and away > 0
    actual = "GG" if both_scored else "NG"
    return "SUCCESS" if pick == actual else "FAILURE"


def _pick_from_decision(decision: str, selection: Any) -> str:
    if decision == "PLAY" and selection:
        return str(selection).upper()
    return "NO_BET"


async def attach_result(
    session: AsyncSession,
    analysis_run_id: int,
    match_id: str,
    final_home_goals: int,
    final_away_goals: int,
    status: str = "FINAL",
    *,
    persist: bool = True,
) -> SnapshotResolution:
    """
    Load predictions for the run, compute per-market outcomes from final score.
    If persist=True, persist SnapshotResolution; if False (e.g. dry_run), return resolution without saving.
    """
    pred_repo = PredictionRepository(session)
    resolution_repo = SnapshotResolutionRepository(session)
    predictions = await pred_repo.list_by_analysis_run(analysis_run_id)

    market_outcomes: Dict[str, str] = {}
    reason_codes_by_market: Dict[str, list] = {"one_x_two": [], "over_under_25": [], "gg_ng": []}

    for p in predictions:
        market = (p.market or "").strip()
        key = MARKET_TO_KEY.get(market) or market.lower()
        if key not in market_outcomes:
            market_outcomes[key] = "NEUTRAL"
        pick = _pick_from_decision(p.decision or "", getattr(p, "pick", None))
        if pick in ("NO_BET", "NO_PREDICTION", ""):
            market_outcomes[key] = "NEUTRAL"
            continue
        if key == "one_x_two":
            market_outcomes[key] = _outcome_1x2(pick, final_home_goals, final_away_goals)
        elif key == "over_under_25":
            market_outcomes[key] = _outcome_ou25(pick, final_home_goals, final_away_goals)
        elif key == "gg_ng":
            market_outcomes[key] = _outcome_ggng(pick, final_home_goals, final_away_goals)
        try:
            reasons = json.loads(p.reasons_json) if getattr(p, "reasons_json", None) else []
            reason_codes_by_market.setdefault(key, []).extend(reasons[:5])
        except Exception:
            pass

    resolution = SnapshotResolution(
        created_at_utc=datetime.now(timezone.utc),
        analysis_run_id=analysis_run_id,
        match_id=match_id,
        final_home_goals=final_home_goals,
        final_away_goals=final_away_goals,
        status=status,
        market_outcomes_json=json.dumps(market_outcomes, sort_keys=True),
        reason_codes_by_market_json=json.dumps(reason_codes_by_market, sort_keys=True),
    )
    if persist:
        await resolution_repo.create(resolution)
    return resolution
