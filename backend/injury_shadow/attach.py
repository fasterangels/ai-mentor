"""
Injury news shadow attach: fetch resolutions, compute features, emit shadow reason codes.
Additive report-only; does not change decisions. Deterministic.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from injury_shadow.features import compute_injury_shadow_features
from analyzer.v2.reason_codes import (
    INJ_MULTIPLE_OUT,
    INJ_HIGH_UNCERTAINTY,
    INJ_CONFLICT_PRESENT,
    INJ_COVERAGE_LOW,
)

# Thresholds for shadow reason codes (deterministic)
INJ_HIGH_UNCERTAINTY_THRESHOLD = 1.0
INJ_MULTIPLE_OUT_MIN = 3
MAX_REASONS_CAP = 10
KEY_ITEMS_TOP_K = 5


def _get(r: Any, key: str, default: Any = None) -> Any:
    if isinstance(r, dict):
        return r.get(key, default)
    return getattr(r, key, default)


async def _fetch_resolutions_for_scope(
    session: Any,
    fixture_id: Optional[str],
    team_refs: List[str],
    policy_version: str,
) -> List[Dict[str, Any]]:
    """
    Fetch resolution records for scope. Deterministic order: team_ref, player_ref, resolution_id.
    Returns [] if InjuryNewsResolutionRepository or table is not available (optional dependency).
    """
    try:
        from repositories.injury_news_resolution_repo import InjuryNewsResolutionRepository

        repo = InjuryNewsResolutionRepository(session)
        if fixture_id:
            rows = await repo.list_by_fixture_and_teams(fixture_id, team_refs, policy_version)
        else:
            rows = await repo.list_by_team_refs(team_refs, policy_version)
        out = []
        for r in rows:
            out.append({
                "resolution_id": _get(r, "resolution_id"),
                "team_ref": _get(r, "team_ref"),
                "player_ref": _get(r, "player_ref"),
                "resolved_status": _get(r, "resolved_status"),
                "resolution_confidence": float(_get(r, "resolution_confidence", 0.0)),
                "resolution_method": _get(r, "resolution_method"),
            })
        out.sort(key=lambda x: (
            str(x.get("team_ref") or ""),
            str(x.get("player_ref") or ""),
            str(x.get("resolution_id") or ""),
        ))
        return out
    except ImportError:
        return []
    except Exception:
        return []


def _build_shadow_reasons_and_evidence(
    resolutions: List[Dict[str, Any]],
    features: Dict[str, Any],
    policy_version: str,
    max_reasons: int = MAX_REASONS_CAP,
) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Emit shadow-only reason codes with evidence pointers. Bounded by max_reasons.
    Returns (reasons, evidence_pointers).
    """
    reasons: List[Dict[str, Any]] = []
    evidence_pointers: List[Dict[str, Any]] = []

    out_count = features.get("out_count", 0)
    uncertainty_index = features.get("uncertainty_index", 0.0)
    has_conflict = any(
        (_get(r, "resolution_method") or "").strip().upper() == "UNRESOLVED_CONFLICT"
        or (_get(r, "resolved_status") or "").strip().upper() == "QUESTIONABLE"
        for r in resolutions
    )
    no_coverage = len(resolutions) == 0

    resolution_ids_used: List[str] = []
    for r in resolutions[:20]:
        rid = _get(r, "resolution_id")
        if rid is not None and str(rid).strip():
            resolution_ids_used.append(str(rid))

    if no_coverage and len(reasons) < max_reasons:
        reasons.append({"code": INJ_COVERAGE_LOW, "text": "No injury/news resolutions for scope"})
        evidence_pointers.append({"code": INJ_COVERAGE_LOW, "policy_version": policy_version, "resolution_ids": []})

    if out_count >= INJ_MULTIPLE_OUT_MIN and len(reasons) < max_reasons:
        reasons.append({"code": INJ_MULTIPLE_OUT, "text": f"Multiple players out (count={out_count})"})
        evidence_pointers.append({
            "code": INJ_MULTIPLE_OUT,
            "policy_version": policy_version,
            "resolution_ids": resolution_ids_used[:5],
        })

    if has_conflict and len(reasons) < max_reasons:
        reasons.append({"code": INJ_CONFLICT_PRESENT, "text": "Unresolved conflict or questionable status present"})
        evidence_pointers.append({
            "code": INJ_CONFLICT_PRESENT,
            "policy_version": policy_version,
            "resolution_ids": resolution_ids_used[:5],
        })

    if uncertainty_index >= INJ_HIGH_UNCERTAINTY_THRESHOLD and len(reasons) < max_reasons:
        reasons.append({
            "code": INJ_HIGH_UNCERTAINTY,
            "text": f"High uncertainty index ({uncertainty_index})",
        })
        evidence_pointers.append({
            "code": INJ_HIGH_UNCERTAINTY,
            "policy_version": policy_version,
            "resolution_ids": resolution_ids_used[:5],
        })

    return reasons[:max_reasons], evidence_pointers[:max_reasons]


async def build_injury_news_shadow_summary(
    session: Any,
    fixture_id: Optional[str],
    team_refs: List[str],
    policy_version: str = "injury_news.v1",
    *,
    top_k: int = KEY_ITEMS_TOP_K,
    max_reasons: int = MAX_REASONS_CAP,
) -> Dict[str, Any]:
    """
    Build injury news shadow summary for report. Does not modify decisions.
    Fetches resolutions (optional repo), computes features, emits shadow reasons with evidence.
    Deterministic; bounded output.
    """
    resolutions = await _fetch_resolutions_for_scope(session, fixture_id, team_refs, policy_version)
    features = compute_injury_shadow_features(resolutions, top_k=top_k)
    reasons, evidence_pointers = _build_shadow_reasons_and_evidence(
        resolutions, features, policy_version, max_reasons=max_reasons
    )
    teams_with_any_resolution = len(set(r.get("team_ref") for r in resolutions if r.get("team_ref")))
    return {
        "enabled": True,
        "policy_version": policy_version,
        "resolutions_count": len(resolutions),
        "team_refs_requested": len(team_refs),
        "teams_with_any_resolution": teams_with_any_resolution,
        "features": {
            "out_count": features["out_count"],
            "questionable_count": features["questionable_count"],
            "suspended_count": features["suspended_count"],
            "unknown_count": features["unknown_count"],
            "uncertainty_index": features["uncertainty_index"],
            "key_items": features["key_items"],
        },
        "reasons": reasons,
        "evidence_pointers": evidence_pointers,
    }
