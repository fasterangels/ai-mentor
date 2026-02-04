"""
End-to-end deterministic shadow pipeline:
ingestion (pipeline) -> analysis -> result attach -> evaluation -> tune/shadow -> audit.
Returns PipelineReport; does not apply policy.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from pipeline.pipeline import run_pipeline
from pipeline.types import PipelineInput, EvidencePack
from evaluation.evaluation_v2 import evidence_pack_to_serializable
from evaluation.offline_eval import build_evaluation_report
from policy.policy_runtime import get_active_policy, min_confidence_from_policy
from policy.policy_store import checksum_report
from policy.tuner import run_tuner, PolicyProposal
from policy.audit import audit_snapshots
from services.result_attach_service import attach_result

# Analyzer v2
from analyzer.v2.engine import analyze_v2
from analyzer.v2.contracts import ANALYZER_VERSION_V2

MARKETS_V2 = ["1X2", "OU_2.5", "BTTS"]


def _evidence_pack_to_dict(ep: EvidencePack) -> Dict[str, Any]:
    """Serializable dict for audit snapshots (roundtrip with evidence_pack_from_dict)."""
    return evidence_pack_to_serializable(ep)


async def run_shadow_pipeline(
    session: AsyncSession,
    connector_name: str,
    match_id: str,
    final_score: Dict[str, int],
    status: str = "FINAL",
    *,
    now_utc: Optional[datetime] = None,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """
    Run full shadow pipeline: pipeline -> analyze -> attach -> eval -> tune -> audit.
    Returns PipelineReport. Does not apply policy.
    If dry_run=True, do not persist SnapshotResolution and do not write cache; still compute reports/checksums.
    """
    from models.analysis_run import AnalysisRun
    from models.prediction import Prediction
    from repositories.analysis_run_repo import AnalysisRunRepository
    from repositories.prediction_repo import PredictionRepository

    now = now_utc or datetime.now(timezone.utc)
    home = int(final_score.get("home", 0))
    away = int(final_score.get("away", 0))

    evidence_pack: Optional[EvidencePack] = None

    if connector_name in ("sample_platform", "stub_platform"):
        # Recorded fixtures (sample_platform) or live stub (stub_platform) via connector
        # stub_platform requires LIVE_IO_ALLOWED=true (enforced via live_io wrapper)
        from ingestion.live_io import get_connector_safe
        from ingestion.evidence_builder import ingested_to_evidence_pack

        adapter = get_connector_safe(connector_name)
        if not adapter:
            return _error_report("CONNECTOR_NOT_FOUND", f"{connector_name} not available or live IO not allowed")
        ingested = adapter.fetch_match_data(match_id)
        if not ingested:
            return _error_report("NO_FIXTURE", f"No fixture found for match_id={match_id!r}")
        # Reuse same ensure logic for both connectors (same ingested data structure)
        await _ensure_sample_platform_match(session, ingested, now)
        evidence_pack = ingested_to_evidence_pack(ingested, captured_at_utc=now)
    else:
        if connector_name == "dummy":
            await _ensure_dummy_match(session, match_id, now)

        # 1) Run pipeline (data fetch + cache) -> evidence_pack
        pipeline_input = PipelineInput(
            match_id=match_id,
            domains=["fixtures", "stats"],
            window_hours=72,
            force_refresh=False,
        )
        pipeline_result = await run_pipeline(session, pipeline_input, dry_run=dry_run)
        evidence_pack = pipeline_result.evidence_pack

    if not evidence_pack:
        return _error_report("NO_EVIDENCE_PACK", "Pipeline returned no evidence pack")

    ep_serialized = evidence_pack_to_serializable(evidence_pack)

    def _strip_volatile(obj: Any) -> Any:
        if isinstance(obj, dict):
            return {k: _strip_volatile(v) for k, v in obj.items() if k not in ("captured_at_utc", "fetched_at_utc")}
        if isinstance(obj, list):
            return [_strip_volatile(x) for x in obj]
        return obj

    # Exclude volatile timestamps so checksum is deterministic for tests
    payload_checksum = checksum_report(_strip_volatile(ep_serialized))
    collected_at = evidence_pack.captured_at_utc.isoformat() if hasattr(evidence_pack.captured_at_utc, "isoformat") else str(evidence_pack.captured_at_utc)

    # 2) Run analyzer (v2)
    current_policy = get_active_policy()
    min_conf = min_confidence_from_policy(current_policy)
    analyzer_payload = analyze_v2("RESOLVED", evidence_pack, MARKETS_V2, min_confidence=min_conf)

    # 3) Persist analysis run + predictions
    run_repo = AnalysisRunRepository(session)
    pred_repo = PredictionRepository(session)
    flags = analyzer_payload.get("analysis_run", {}).get("flags") or []
    counts = analyzer_payload.get("analysis_run", {}).get("counts") or {}
    run = AnalysisRun(
        created_at_utc=now,
        logic_version=ANALYZER_VERSION_V2,
        mode="PREGAME",
        match_id=match_id,
        data_quality_score=0.8,
        flags_json=json.dumps(flags),
    )
    await run_repo.create(run)
    await session.flush()
    snapshot_id = run.id

    ep_json = json.dumps(_evidence_pack_to_dict(evidence_pack), default=str)
    for dec in analyzer_payload.get("decisions") or []:
        market = dec.get("market") or ""
        decision = dec.get("decision") or "NO_PREDICTION"
        pick = dec.get("selection")
        confidence = dec.get("confidence")
        confidence = float(confidence) if confidence is not None else 0.0
        reasons = dec.get("reasons") or []
        probs = dec.get("probabilities") or {}
        pred = Prediction(
            created_at_utc=now,
            analysis_run_id=run.id,
            match_id=match_id,
            market=market,
            decision=decision,
            pick=str(pick) if pick is not None else None,
            probabilities_json=json.dumps(probs),
            separation=0.0,
            confidence=confidence,
            risk=max(0.0, 1.0 - confidence),
            reasons_json=json.dumps(reasons),
            evidence_pack_json=ep_json,
        )
        await pred_repo.create(pred)

    # 4) Attach result (SnapshotResolution); skip persist when dry_run
    resolution = await attach_result(
        session, snapshot_id, match_id, home, away, status, persist=not dry_run
    )
    market_outcomes = json.loads(resolution.market_outcomes_json) if isinstance(resolution.market_outcomes_json, str) else resolution.market_outcomes_json

    # 5) Evaluation report (in-process)
    eval_report = await build_evaluation_report(session, limit=5000)
    evaluation_report_checksum = checksum_report(eval_report)

    # 6) Tuner (shadow)
    proposal: PolicyProposal = run_tuner(eval_report)
    proposal_dump = proposal.proposed_policy.model_dump(mode="json")
    # Exclude volatile meta.created_at_utc for deterministic checksum
    if "meta" in proposal_dump and isinstance(proposal_dump["meta"], dict):
        proposal_dump = {**proposal_dump, "meta": {k: v for k, v in proposal_dump["meta"].items() if k != "created_at_utc"}}
    proposal_checksum = checksum_report(proposal_dump)

    # 7) Audit (same snapshot set)
    snapshots = [{"match_id": match_id, "evidence_pack": _evidence_pack_to_dict(evidence_pack)}]
    audit_report = audit_snapshots(snapshots, current_policy, proposal.proposed_policy)

    # Build PipelineReport
    analysis_picks: Dict[str, Any] = {}
    for dec in analyzer_payload.get("decisions") or []:
        m = dec.get("market")
        if m:
            analysis_picks[m] = {
                "pick": dec.get("selection") or dec.get("decision"),
                "confidence": dec.get("confidence"),
            }

    report: Dict[str, Any] = {
        "ingestion": {
            "payload_checksum": payload_checksum,
            "collected_at": collected_at,
        },
        "analysis": {
            "snapshot_id": snapshot_id,
            "markets_picks_confidences": analysis_picks,
        },
        "resolution": {
            "market_outcomes": market_outcomes,
        },
        "evaluation_report_checksum": evaluation_report_checksum,
        "proposal": {
            "diffs": [list(d) for d in proposal.diffs],
            "guardrails_results": [list(g) for g in proposal.guardrails_results],
            "proposal_checksum": proposal_checksum,
        },
        "audit": {
            "changed_count": audit_report["summary"]["changed_count"],
            "per_market_change_count": audit_report["summary"]["per_market_change_count"],
            "snapshots_checksum": audit_report["snapshots_checksum"],
            "current_policy_checksum": audit_report["current_policy_checksum"],
            "proposed_policy_checksum": audit_report["proposed_policy_checksum"],
        },
    }
    if dry_run:
        report["dry_run"] = True
    return report


def _slug(s: str, max_len: int = 32) -> str:
    """Deterministic slug for IDs (lowercase, spaces -> underscore)."""
    out = "".join(c if c.isalnum() or c in " -_" else "" for c in (s or ""))
    out = out.replace(" ", "_").lower().strip("_") or "unknown"
    return out[:max_len]


async def _ensure_sample_platform_match(
    session: AsyncSession, ingested: Any, kickoff: datetime
) -> None:
    """Ensure match exists for sample_platform connector from ingested fixture data."""
    from models.match import Match
    from models.competition import Competition
    from models.season import Season
    from models.team import Team
    from repositories.match_repo import MatchRepository

    match_id = ingested.match_id
    match_repo = MatchRepository(session)
    existing = await match_repo.get_by_id(match_id)
    if existing:
        return

    comp_slug = _slug(ingested.competition, 24)
    comp_id = f"sample_platform_comp_{comp_slug}"
    season_id = "sample_platform_season_1"
    home_id = f"sample_platform_team_{_slug(ingested.home_team)}"
    away_id = f"sample_platform_team_{_slug(ingested.away_team)}"

    if await session.get(Competition, comp_id) is None:
        session.add(Competition(id=comp_id, name=ingested.competition, country="XX", tier=1, is_active=True))
    if await session.get(Season, season_id) is None:
        session.add(Season(id=season_id, competition_id=comp_id, name="2025", year_start=2025, year_end=2026, is_active=True))
    if await session.get(Team, home_id) is None:
        session.add(Team(id=home_id, name=ingested.home_team, country="XX", is_active=True))
    if await session.get(Team, away_id) is None:
        session.add(Team(id=away_id, name=ingested.away_team, country="XX", is_active=True))
    await session.flush()

    kickoff_dt = datetime.fromisoformat(ingested.kickoff_utc.replace("Z", "+00:00"))
    if kickoff_dt.tzinfo is None:
        kickoff_dt = kickoff_dt.replace(tzinfo=timezone.utc)

    session.add(Match(
        id=match_id,
        competition_id=comp_id,
        season_id=season_id,
        kickoff_utc=kickoff_dt,
        status="FINAL",
        home_team_id=home_id,
        away_team_id=away_id,
    ))
    await session.flush()


async def _ensure_dummy_match(session: AsyncSession, match_id: str, kickoff: datetime) -> None:
    """Ensure match exists for dummy connector (create competition, season, teams, match if missing)."""
    from models.match import Match
    from models.competition import Competition
    from models.season import Season
    from models.team import Team
    from repositories.match_repo import MatchRepository

    match_repo = MatchRepository(session)
    existing = await match_repo.get_by_id(match_id)
    if existing:
        return
    comp_id = "shadow-dummy-comp"
    season_id = "shadow-dummy-season"
    home_id = "shadow-dummy-home"
    away_id = "shadow-dummy-away"
    if await session.get(Competition, comp_id) is None:
        session.add(Competition(id=comp_id, name="Dummy League", country="XX", tier=1, is_active=True))
    if await session.get(Season, season_id) is None:
        session.add(Season(id=season_id, competition_id=comp_id, name="2025", year_start=2025, year_end=2026, is_active=True))
    if await session.get(Team, home_id) is None:
        session.add(Team(id=home_id, name="Dummy Home", country="XX", is_active=True))
    if await session.get(Team, away_id) is None:
        session.add(Team(id=away_id, name="Dummy Away", country="XX", is_active=True))
    await session.flush()
    session.add(Match(
        id=match_id,
        competition_id=comp_id,
        season_id=season_id,
        kickoff_utc=kickoff,
        status="FINAL",
        home_team_id=home_id,
        away_team_id=away_id,
    ))
    await session.flush()


def _error_report(reason: str, detail: str) -> Dict[str, Any]:
    return {
        "ingestion": {"payload_checksum": None, "collected_at": None},
        "analysis": {"snapshot_id": None, "markets_picks_confidences": {}},
        "resolution": {"market_outcomes": {}},
        "evaluation_report_checksum": None,
        "proposal": {"diffs": [], "guardrails_results": [], "proposal_checksum": None},
        "audit": {"changed_count": 0, "per_market_change_count": {}, "snapshots_checksum": None, "current_policy_checksum": None, "proposed_policy_checksum": None},
        "error": reason,
        "detail": detail,
    }
