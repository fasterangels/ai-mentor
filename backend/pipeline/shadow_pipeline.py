"""
End-to-end deterministic shadow pipeline:
ingestion (pipeline) -> analysis -> result attach -> evaluation -> tune/shadow -> audit.
Returns PipelineReport; does not apply policy.
"""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

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
from ops.ops_events import (
    log_pipeline_start,
    log_pipeline_end,
    log_ingestion_source,
    log_evaluation_summary,
    log_guardrail_trigger,
)

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
    hard_block_persistence: bool = False,
    activation: bool = False,
    allow_activation_for_this_match: Optional[bool] = None,
) -> Dict[str, Any]:
    """
    Run full shadow pipeline: pipeline -> analyze -> attach -> eval -> tune -> audit.
    Returns PipelineReport. Does not apply policy.
    If dry_run=True, do not persist SnapshotResolution and do not write cache; still compute reports/checksums.
    If hard_block_persistence=True, skip ALL DB writes (AnalysisRun, Prediction, SnapshotResolution, cache).
    If activation=True, check activation gate and only persist if allowed (still requires env gates).
    If allow_activation_for_this_match is False (rollout/daily cap), do not persist even if gate passes.
    """
    from models.analysis_run import AnalysisRun
    from models.prediction import Prediction
    from repositories.analysis_run_repo import AnalysisRunRepository
    from repositories.prediction_repo import PredictionRepository

    now = now_utc or datetime.now(timezone.utc)
    home = int(final_score.get("home", 0))
    away = int(final_score.get("away", 0))

    t_start = log_pipeline_start(connector_name, match_id)
    evidence_pack: Optional[EvidencePack] = None

    if connector_name in ("sample_platform", "stub_platform", "stub_live_platform"):
        # Recorded fixtures (sample_platform) or live stubs (stub_platform/stub_live_platform) via get_connector_safe
        # Live connectors require LIVE_IO_ALLOWED=true and execution_mode=shadow with recorded baseline
        from ingestion.live_io import execution_mode_context, get_connector_safe, record_request
        from ingestion.evidence_builder import ingested_to_evidence_pack

        with execution_mode_context("shadow"):
            adapter = get_connector_safe(connector_name)
        if not adapter:
            log_guardrail_trigger("connector_not_found", f"{connector_name} not available or live IO not allowed")
            log_pipeline_end(connector_name, match_id, time.perf_counter() - t_start, error="CONNECTOR_NOT_FOUND")
            return _error_report("CONNECTOR_NOT_FOUND", f"{connector_name} not available or live IO not allowed")
        # Record live IO metrics for stub_platform / stub_live_platform (not for recorded sample_platform)
        if connector_name in ("stub_platform", "stub_live_platform"):
            t0 = time.perf_counter()
        ingested = adapter.fetch_match_data(match_id)
        if connector_name in ("stub_platform", "stub_live_platform"):
            latency_ms = (time.perf_counter() - t0) * 1000
            record_request(success=ingested is not None, latency_ms=latency_ms)
        if not ingested:
            log_guardrail_trigger("no_fixture", f"No fixture found for match_id={match_id!r}")
            log_pipeline_end(connector_name, match_id, time.perf_counter() - t_start, error="NO_FIXTURE")
            return _error_report("NO_FIXTURE", f"No fixture found for match_id={match_id!r}")
        # Reuse same ensure logic for both connectors (same ingested data structure)
        await _ensure_sample_platform_match(session, ingested, now)
        evidence_pack = ingested_to_evidence_pack(ingested, captured_at_utc=now)
        source = "recorded" if connector_name == "sample_platform" else "live"
        log_ingestion_source(connector_name, source, match_id)
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
        pipeline_result = await run_pipeline(session, pipeline_input, dry_run=dry_run or hard_block_persistence)
        evidence_pack = pipeline_result.evidence_pack
        log_ingestion_source(connector_name, "recorded", match_id)

    if not evidence_pack:
        log_guardrail_trigger("no_evidence_pack", "Pipeline returned no evidence pack")
        log_pipeline_end(connector_name, match_id, time.perf_counter() - t_start, error="NO_EVIDENCE_PACK")
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

    # 2.5) Check activation gate for each decision
    activation_audits: List[Dict[str, Any]] = []
    activation_allowed_for_match = False
    from activation.audit import create_activation_audit

    decisions_list = analyzer_payload.get("decisions") or []
    # Rollout/daily cap: if explicitly False, do not allow activation for this match
    if allow_activation_for_this_match is False and activation:
        activation_allowed_for_match = False
        log_guardrail_trigger("activation_cap", "rollout or daily cap limited", cap_value=0)
        for dec in decisions_list:
            audit = await create_activation_audit(
                session=session,
                connector_name=connector_name,
                match_id=match_id,
                market=dec.get("market") or "",
                decision=dec,
                confidence=float(dec.get("confidence") or 0.0),
                reasons=dec.get("reasons") or [],
                activation_allowed=False,
                activation_reason="rollout or daily cap limited",
                now_utc=now,
            )
            activation_audits.append(audit)
    # If activation is requested, check gates; otherwise all decisions are shadow-only
    elif activation and not hard_block_persistence and not dry_run:
        from activation.gate import check_activation_gate

        for dec in decisions_list:
            market = dec.get("market") or ""
            confidence = float(dec.get("confidence") or 0.0)
            reasons = dec.get("reasons") or []

            allowed, reason = check_activation_gate(
                connector_name=connector_name,
                market=market,
                confidence=confidence,
                policy_min_confidence=min_conf,
            )

            audit = await create_activation_audit(
                session=session,
                connector_name=connector_name,
                match_id=match_id,
                market=market,
                decision=dec,
                confidence=confidence,
                reasons=reasons,
                activation_allowed=allowed,
                activation_reason=reason,
                now_utc=now,
            )
            activation_audits.append(audit)

            if allowed:
                activation_allowed_for_match = True
    else:
        # If activation not requested or blocked, all decisions are shadow-only
        for dec in decisions_list:
            market = dec.get("market") or ""
            confidence = float(dec.get("confidence") or 0.0)
            reasons = dec.get("reasons") or []
            audit = await create_activation_audit(
                session=session,
                connector_name=connector_name,
                match_id=match_id,
                market=market,
                decision=dec,
                confidence=confidence,
                reasons=reasons,
                activation_allowed=False,
                activation_reason="activation=False or persistence blocked" if not activation else "hard_block_persistence or dry_run",
                now_utc=now,
            )
            activation_audits.append(audit)

    # 3) Persist analysis run + predictions
    # Skip if: hard_block_persistence, dry_run, or (activation=False OR activation=True but gates failed)
    snapshot_id: Optional[int] = None
    should_persist = not hard_block_persistence and not dry_run
    if activation:
        # When activation is requested, only persist if gates passed
        should_persist = should_persist and activation_allowed_for_match
    else:
        # When activation=False (default), shadow-only (no writes)
        should_persist = False
    if should_persist:
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
    else:
        # For hard_block_persistence, use placeholder snapshot_id for attach_result
        snapshot_id = None

    # 4) Attach result (SnapshotResolution); skip persist when dry_run, hard_block_persistence, or activation not allowed
    resolution = await attach_result(
        session, snapshot_id or 0, match_id, home, away, status, persist=should_persist and not dry_run
    )
    market_outcomes = json.loads(resolution.market_outcomes_json) if isinstance(resolution.market_outcomes_json, str) else resolution.market_outcomes_json

    # 5) Evaluation report (in-process)
    eval_report = await build_evaluation_report(session, limit=5000)
    overall = eval_report.get("overall") or {}
    match_count = int(overall.get("total_snapshots", 0))
    resolved_count = int(overall.get("resolved_snapshots", 0))
    accuracy_by_market: Dict[str, float] = {}
    for m, data in (eval_report.get("per_market_accuracy") or {}).items():
        acc = data.get("accuracy")
        if acc is not None:
            accuracy_by_market[m] = acc
    log_evaluation_summary(match_count, resolved_count, accuracy_by_market if accuracy_by_market else None)
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
    decisions_list = analyzer_payload.get("decisions") or []
    for dec in decisions_list:
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
            "snapshot_id": snapshot_id if snapshot_id is not None else None,
            "markets_picks_confidences": analysis_picks,
            "decisions": decisions_list,  # Include full decisions for guardrails (reasons, etc.)
        },
        "resolution": {
            "market_outcomes": market_outcomes,
        },
        "evaluation_report_checksum": evaluation_report_checksum,
        "proposal": {
            "diffs": [list(d) for d in proposal.diffs],
            "guardrails_results": [list(g) for g in proposal.guardrails_results],
            "proposal_checksum": proposal_checksum,
            "tuner_constraints_summary": getattr(proposal, "tuner_constraints_summary", None) or {},
        },
        "audit": {
            "changed_count": audit_report["summary"]["changed_count"],
            "per_market_change_count": audit_report["summary"]["per_market_change_count"],
            "snapshots_checksum": audit_report["snapshots_checksum"],
            "current_policy_checksum": audit_report["current_policy_checksum"],
            "proposed_policy_checksum": audit_report["proposed_policy_checksum"],
        },
        "activation": {
            "activated": activation_allowed_for_match if activation else False,
            "reason": activation_audits[0].get("activation_reason") if activation_audits and not activation_allowed_for_match else None,
            "audits": activation_audits,
        },
    }
    if dry_run:
        report["dry_run"] = True
    log_pipeline_end(connector_name, match_id, time.perf_counter() - t_start)
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
        "proposal": {"diffs": [], "guardrails_results": [], "proposal_checksum": None, "tuner_constraints_summary": {}},
        "audit": {"changed_count": 0, "per_market_change_count": {}, "snapshots_checksum": None, "current_policy_checksum": None, "proposed_policy_checksum": None},
        "error": reason,
        "detail": detail,
    }
