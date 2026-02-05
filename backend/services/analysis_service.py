"""Analysis flow: resolver → pipeline → analyzer. Minimal composition only."""

from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from pipeline.types import EvidencePack

from sqlalchemy.ext.asyncio import AsyncSession

from resolver.match_resolver import resolve_match
from resolver.types import MatchResolutionInput, MatchResolutionOutput
from pipeline.pipeline import run_pipeline
from pipeline.types import PipelineInput
from analyzer.engine_v1 import analyze
from analyzer.types import AnalyzerInput, AnalyzerPolicy, AnalyzerResult
from analyzer.v2.engine import analyze_v2
from analyzer.v2.contracts import ANALYZER_VERSION_DEFAULT
from policy.policy_runtime import get_active_policy, min_confidence_from_policy
from evaluation.evaluation_v2 import (
    compute_evidence_pack_hash,
    compute_metrics,
    compute_output_hash,
    run_stability_check,
)


def _normalize_market_for_v2(market: str) -> str:
    """Map v1-style market names to v2 supported names."""
    m = (market or "").strip().upper()
    if m == "OU25" or m == "OU_25":
        return "OU_2.5"
    if m == "GGNG" or m == "BTTS":
        return "BTTS"
    if m == "1X2":
        return "1X2"
    return market or "1X2"


def _parse_kickoff(s: Optional[str]) -> Optional[datetime]:
    if not s:
        return None
    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except (ValueError, AttributeError):
        return None


def _resolver_to_dict(out: MatchResolutionOutput) -> Dict[str, Any]:
    return {
        "status": out.status,
        "match_id": out.match_id,
        "candidates": [
            {
                "match_id": c.match_id,
                "kickoff_utc": c.kickoff_utc.isoformat() if hasattr(c.kickoff_utc, "isoformat") else str(c.kickoff_utc),
                "competition_id": c.competition_id,
            }
            for c in (out.candidates or [])
        ],
        "notes": out.notes or [],
    }


def _evidence_pack_to_dict(ep: Optional[EvidencePack]) -> Optional[Dict[str, Any]]:
    if ep is None:
        return None
    return {
        "match_id": ep.match_id,
        "domains": list(ep.domains.keys()) if ep.domains else [],
        "captured_at_utc": ep.captured_at_utc.isoformat() if hasattr(ep.captured_at_utc, "isoformat") else str(ep.captured_at_utc),
        "flags": getattr(ep, "flags", []) or [],
    }


def _analyzer_to_dict(result: AnalyzerResult) -> Dict[str, Any]:
    return {
        "status": result.status,
        "analysis_run": {
            "logic_version": result.analysis_run.logic_version,
            "flags": result.analysis_run.flags,
        },
        "decisions": [
            {
                "market": d.market,
                "decision": d.decision,
                "probabilities": d.probabilities,
                "separation": d.separation,
                "confidence": d.confidence,
                "risk": d.risk,
                "reasons": d.reasons,
            }
            for d in result.decisions
        ],
    }


async def run_analysis_flow(session: AsyncSession, request: Dict[str, Any]) -> Dict[str, Any]:
    """
    Resolver → (if RESOLVED) pipeline → analyzer. Return 200-friendly dict.
    """
    home_text = request.get("home_text") or ""
    away_text = request.get("away_text") or ""
    kickoff_hint_utc = _parse_kickoff(request.get("kickoff_hint_utc"))
    window_hours = int(request.get("window_hours") or 24)
    competition_id = request.get("competition_id")
    mode = request.get("mode") or "PREGAME"
    markets = request.get("markets") or ["1X2", "OU25", "GGNG"]
    policy_dict = request.get("policy") or {}
    analyzer_version = request.get("analyzer_version") or ANALYZER_VERSION_DEFAULT

    resolver_input = MatchResolutionInput(
        home_text=home_text,
        away_text=away_text,
        kickoff_hint_utc=kickoff_hint_utc,
        window_hours=window_hours,
        competition_id=competition_id,
    )
    resolver_output: MatchResolutionOutput = await resolve_match(resolver_input, session)

    if resolver_output.status == "AMBIGUOUS":
        return {
            "status": "AMBIGUOUS",
            "match_id": None,
            "resolver": _resolver_to_dict(resolver_output),
            "evidence_pack": None,
            "analyzer": None,
        }
    if resolver_output.status == "NOT_FOUND":
        return {
            "status": "NOT_FOUND",
            "match_id": None,
            "resolver": _resolver_to_dict(resolver_output),
            "evidence_pack": None,
            "analyzer": None,
        }

    match_id = resolver_output.match_id
    if not match_id:
        return {
            "status": "NO_PREDICTION",
            "match_id": None,
            "resolver": _resolver_to_dict(resolver_output),
            "evidence_pack": None,
            "analyzer": None,
        }

    pipeline_input = PipelineInput(
        match_id=match_id,
        domains=["fixtures", "stats"],
        window_hours=window_hours,
        force_refresh=False,
    )
    pipeline_result = await run_pipeline(session, pipeline_input)
    evidence_pack = pipeline_result.evidence_pack

    # Read thresholds from policy (file or default); request can override
    active_policy = get_active_policy()
    min_confidence = float(
        policy_dict.get("min_confidence")
        if policy_dict.get("min_confidence") is not None
        else min_confidence_from_policy(active_policy)
    )

    if analyzer_version == "v2":
        markets_v2 = [_normalize_market_for_v2(m) for m in markets]
        t0 = time.perf_counter()
        analyzer_payload = analyze_v2(
            resolver_status=resolver_output.status,
            evidence_pack=evidence_pack,
            markets=markets_v2,
            min_confidence=min_confidence,
        )
        runtime_ms = (time.perf_counter() - t0) * 1000.0
        output_hash = compute_output_hash(analyzer_payload)
        stability = run_stability_check(match_id, evidence_pack, analyzer_payload)
        evaluation_v2 = compute_metrics(analyzer_payload, runtime_ms, output_hash)
        evaluation_v2["stability"] = stability
        return {
            "status": "OK" if analyzer_payload["status"] == "OK" else "NO_PREDICTION",
            "match_id": match_id,
            "resolver": _resolver_to_dict(resolver_output),
            "evidence_pack": _evidence_pack_to_dict(evidence_pack),
            "analyzer": analyzer_payload,
            "evaluation_v2": evaluation_v2,
        }
    else:
        policy = AnalyzerPolicy(
            min_sep_1x2=float(policy_dict.get("min_sep_1x2", 0.10)),
            min_sep_ou=float(policy_dict.get("min_sep_ou", 0.08)),
            min_sep_gg=float(policy_dict.get("min_sep_gg", 0.08)),
            min_confidence=min_confidence,
            risk_caps=policy_dict.get("risk_caps") or {"default": 0.35},
        )
        analyzer_input = AnalyzerInput(
            analysis_run_id=f"run-{match_id}",
            match_id=match_id,
            mode=mode,
            markets=markets,
            policy=policy,
            evidence_pack=evidence_pack,
        )
        analyzer_result: AnalyzerResult = analyze(analyzer_input)
        return {
            "status": "OK" if analyzer_result.status == "OK" else "NO_PREDICTION",
            "match_id": match_id,
            "resolver": _resolver_to_dict(resolver_output),
            "evidence_pack": _evidence_pack_to_dict(evidence_pack),
            "analyzer": _analyzer_to_dict(analyzer_result),
        }
