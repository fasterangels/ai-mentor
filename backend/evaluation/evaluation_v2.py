"""Evaluation v2: Coverage, abstention, stability metrics for Analyzer v2.

BLOCK 12 — Metrics schema, output hashing, stability check, no ROI.
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
from collections import Counter
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from pipeline.types import DomainData, EvidencePack, QualityReport

logger = logging.getLogger(__name__)


def evidence_pack_from_dict(d: Dict[str, Any]) -> EvidencePack:
    """Build EvidencePack from a serialized dict (e.g. JSON from file). For offline harness."""
    domains: Dict[str, Any] = {}
    for name, dom in (d.get("domains") or {}).items():
        quality = dom.get("quality") or {}
        qr = QualityReport(
            passed=bool(quality.get("passed", False)),
            score=float(quality.get("score", 0.0)),
            flags=list(quality.get("flags") or []),
        )
        dd = DomainData(
            data=dict(dom.get("data") or {}),
            quality=qr,
            sources=list(dom.get("sources") or []),
        )
        domains[name] = dd
    captured = d.get("captured_at_utc")
    if isinstance(captured, str):
        try:
            captured = datetime.fromisoformat(captured.replace("Z", "+00:00"))
            if captured.tzinfo is None:
                captured = captured.replace(tzinfo=timezone.utc)
        except (ValueError, AttributeError):
            captured = datetime.now(timezone.utc)
    else:
        captured = datetime.now(timezone.utc)
    return EvidencePack(
        match_id=str(d.get("match_id", "")),
        domains=domains,
        captured_at_utc=captured,
        flags=list(d.get("flags") or []),
    )

# In-memory stability store: input_hash -> (output_hash, timestamp).
# For multi-process, use a shared store (Redis/DB); see docs.
_STABILITY_STORE: Dict[str, Tuple[str, float]] = {}
TOP_FLAGS_LIMIT = 10
TOP_GATES_LIMIT = 10


def _sorted_json_dumps(obj: Any) -> str:
    """Canonical JSON string (sort_keys=True, no whitespace) for hashing."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str)


def evidence_pack_to_serializable(ep: Optional[EvidencePack]) -> Dict[str, Any]:
    """Serialize EvidencePack to a dict suitable for hashing (full content)."""
    if ep is None:
        return {"_": "none"}
    out: Dict[str, Any] = {
        "match_id": getattr(ep, "match_id", ""),
        "flags": list(getattr(ep, "flags", []) or []),
        "captured_at_utc": str(getattr(ep, "captured_at_utc", "")),
        "domains": {},
    }
    domains = getattr(ep, "domains", {}) or {}
    for name, domain_data in domains.items():
        data = getattr(domain_data, "data", {})
        quality = getattr(domain_data, "quality", None)
        quality_dict = {}
        if quality is not None:
            quality_dict = {
                "passed": getattr(quality, "passed", False),
                "score": getattr(quality, "score", 0.0),
                "flags": list(getattr(quality, "flags", []) or []),
            }
        out["domains"][name] = {
            "data": data,
            "quality": quality_dict,
            "sources": list(getattr(domain_data, "sources", []) or []),
        }
    return out


def compute_evidence_pack_hash(ep: Optional[EvidencePack]) -> str:
    """Stable hash of evidence pack content."""
    obj = evidence_pack_to_serializable(ep)
    return hashlib.sha256(_sorted_json_dumps(obj).encode()).hexdigest()[:32]


def compute_input_hash(match_id: str, evidence_pack_hash: str) -> str:
    """Stable hash of analyzer input (match_id + evidence_pack hash)."""
    raw = f"{match_id}:{evidence_pack_hash}"
    return hashlib.sha256(raw.encode()).hexdigest()[:32]


def compute_output_hash(analyzer_payload: Dict[str, Any]) -> str:
    """Stable hash of v2 analyzer output (decisions + analysis_run subset)."""
    # Only hash the decision-relevant parts for stability
    subset = {
        "status": analyzer_payload.get("status"),
        "version": analyzer_payload.get("version"),
        "decisions": analyzer_payload.get("decisions"),
        "analysis_run": {
            "flags": analyzer_payload.get("analysis_run", {}).get("flags"),
            "counts": analyzer_payload.get("analysis_run", {}).get("counts"),
        },
    }
    return hashlib.sha256(_sorted_json_dumps(subset).encode()).hexdigest()[:32]


def compute_metrics(
    analyzer_payload: Dict[str, Any],
    runtime_ms: float,
    output_hash: str,
) -> Dict[str, Any]:
    """
    Build evaluation_v2 metrics: coverage, abstention, gate failures, runtime, hash.
    """
    decisions: List[Dict[str, Any]] = analyzer_payload.get("decisions") or []
    analysis_run = analyzer_payload.get("analysis_run") or {}
    gate_results: List[Dict[str, Any]] = analysis_run.get("gate_results") or []
    global_flags: List[str] = analysis_run.get("flags") or []

    # Decisions by kind per market
    decisions_by_kind: Dict[str, Dict[str, int]] = {}
    for d in decisions:
        market = d.get("market", "?")
        if market not in decisions_by_kind:
            decisions_by_kind[market] = {"PLAY": 0, "NO_BET": 0, "NO_PREDICTION": 0}
        kind = d.get("decision", "NO_PREDICTION")
        if kind in decisions_by_kind[market]:
            decisions_by_kind[market][kind] += 1

    # Top flags frequency (across decisions + global)
    all_flags: List[str] = list(global_flags)
    for d in decisions:
        all_flags.extend(d.get("flags") or [])
    top_flags = [{"flag": k, "count": v} for k, v in Counter(all_flags).most_common(TOP_FLAGS_LIMIT)]

    # Gate failure frequency
    failed = [g for g in gate_results if g.get("pass") is False]
    gate_fail_counts = Counter(g.get("gate_id", "?") for g in failed)
    gate_failure_frequency = [
        {"gate_id": k, "count": v} for k, v in gate_fail_counts.most_common(TOP_GATES_LIMIT)
    ]

    return {
        "decisions_by_kind_per_market": decisions_by_kind,
        "top_flags_frequency": top_flags,
        "gate_failure_frequency": gate_failure_frequency,
        "analyzer_runtime_ms": round(runtime_ms, 2),
        "output_hash": output_hash,
    }


def check_stability(input_hash: str, output_hash: str) -> Tuple[bool, bool]:
    """
    Check if this input_hash was seen before with a different output_hash.
    Returns (is_stable, trigger_guardrail).
    """
    prev = _STABILITY_STORE.get(input_hash)
    if prev is None:
        return True, False
    prev_output_hash, _ = prev
    if prev_output_hash != output_hash:
        return False, True
    return True, False


def record_stability(input_hash: str, output_hash: str) -> None:
    """Record input_hash -> output_hash for future stability checks."""
    _STABILITY_STORE[input_hash] = (output_hash, time.time())


def run_stability_check(
    match_id: str,
    evidence_pack: Optional[EvidencePack],
    analyzer_payload: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Compute input/output hashes, run stability check, optionally add
    INTERNAL_GUARDRAIL_TRIGGERED and log. Returns dict with input_hash, output_hash,
    stable, guardrail_triggered; and mutates analyzer_payload flags if needed.
    """
    ep_hash = compute_evidence_pack_hash(evidence_pack)
    input_hash = compute_input_hash(match_id, ep_hash)
    output_hash = compute_output_hash(analyzer_payload)
    stable, trigger = check_stability(input_hash, output_hash)
    record_stability(input_hash, output_hash)

    if trigger:
        run_flags = (analyzer_payload.get("analysis_run") or {}).get("flags") or []
        if "INTERNAL_GUARDRAIL_TRIGGERED" not in run_flags:
            run_flags.append("INTERNAL_GUARDRAIL_TRIGGERED")
            if "analysis_run" not in analyzer_payload:
                analyzer_payload["analysis_run"] = {}
            analyzer_payload["analysis_run"]["flags"] = run_flags
        logger.error(
            "evaluation_v2 stability mismatch: input_hash=%s previous_output_hash differs from current output_hash=%s",
            input_hash,
            output_hash,
        )

    return {
        "input_hash": input_hash,
        "output_hash": output_hash,
        "stable": stable,
        "guardrail_triggered": trigger,
    }
