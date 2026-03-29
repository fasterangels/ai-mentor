"""
Deterministic injury/news resolver: turns stored claims into canonical resolutions.
Uses versioned policy JSON. Same DB + policy => same resolutions. No live IO.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.injury_news_claim import InjuryNewsClaim
from models.injury_news_report import InjuryNewsReport
from models.injury_news_resolution import InjuryNewsResolution
from repositories.injury_news_resolution_repo import InjuryNewsResolutionRepository

RESOLVED_STATUS_VALUES = frozenset({"AVAILABLE", "QUESTIONABLE", "OUT", "SUSPENDED", "UNKNOWN"})
DEFAULT_SOURCE_WEIGHT = 0.1


def _policy_path(version: str) -> Path:
    """Path to policy JSON (e.g. injury_news.v1 -> policies/injury_news.v1.json)."""
    base = Path(__file__).resolve().parent.parent
    return base / "policies" / f"{version}.json"


def load_policy(version: str) -> Dict[str, Any]:
    """Load policy JSON by version. Raises FileNotFoundError if missing."""
    path = _policy_path(version)
    text = path.read_text(encoding="utf-8")
    return json.loads(text)


def _claim_status_to_resolved(status: str) -> str:
    """Map claim status to resolved_status. Deterministic."""
    m = {"OUT": "OUT", "DOUBTFUL": "QUESTIONABLE", "FIT": "AVAILABLE", "SUSPENDED": "SUSPENDED", "UNKNOWN": "UNKNOWN"}
    return m.get(status.upper(), "UNKNOWN")


@dataclass
class _ClaimRow:
    """Claim with report info for scoring."""
    claim_id: int
    team_ref: str
    player_ref: Optional[str]
    claim_type: str
    status: str
    confidence: float
    adapter_key: str
    recorded_at: datetime
    published_at: Optional[datetime]


def _max_age_hours(policy: Dict[str, Any], claim_type: str) -> float:
    """Max age in hours for claim_type from policy."""
    by_type = policy.get("max_age_hours_by_claim_type") or {}
    return float(by_type.get(claim_type, 168))


def _ensure_utc(dt: Optional[datetime]) -> Optional[datetime]:
    """Return datetime with timezone (UTC). If naive, assume UTC."""
    if dt is None:
        return None
    if dt.tzinfo is not None:
        return dt
    return dt.replace(tzinfo=timezone.utc)


def _is_stale(row: _ClaimRow, policy: Dict[str, Any], now: datetime) -> bool:
    """True if claim is past max_age for its claim_type."""
    ts = row.published_at or row.recorded_at
    ts = _ensure_utc(ts) or ts
    age_hours = (now - ts).total_seconds() / 3600.0
    return age_hours > _max_age_hours(policy, row.claim_type)


def _score_claim(row: _ClaimRow, policy: Dict[str, Any], now: datetime) -> float:
    """Deterministic score: source_weight * recency_weight * confidence."""
    source_priority = policy.get("source_priority") or {}
    w = float(source_priority.get(row.adapter_key, DEFAULT_SOURCE_WEIGHT))
    half_life = float(policy.get("recency_half_life_hours", 24))
    ts = _ensure_utc(row.published_at or row.recorded_at) or (row.published_at or row.recorded_at)
    age_hours = (now - ts).total_seconds() / 3600.0
    recency = 0.5 ** (age_hours / half_life) if half_life else 1.0
    return w * recency * row.confidence


def _normalize_confidence(score: float, policy: Dict[str, Any]) -> float:
    """Clamp resolution_confidence to [0, 1]. Max possible score = max(source_priority) * 1 * 1."""
    source_priority = policy.get("source_priority") or {}
    max_w = max((float(v) for v in source_priority.values()), default=1.0)
    max_score = max_w * 1.0 * 1.0
    if max_score <= 0:
        return 0.0
    return min(1.0, max(0.0, score / max_score))


def _resolve_group(
    candidates: List[_ClaimRow],
    policy: Dict[str, Any],
    now: datetime,
) -> Dict[str, Any]:
    """
    Resolve one (team_ref, player_ref) group. Candidates already sorted by score desc, then recorded_at desc, claim_id.
    Returns dict for InjuryNewsResolution (fixture_id, team_ref, player_ref, resolved_status, resolution_confidence,
    resolution_method, winning_claim_id, supporting_claim_ids, conflicting_claim_ids, policy_version, created_at).
    """
    policy_version = str(policy.get("policy_version", ""))
    conflict_epsilon = float(policy.get("conflict_epsilon", 0.05))
    conflict_behavior = str(policy.get("conflict_behavior", "QUESTIONABLE")).strip().upper()
    if conflict_behavior not in RESOLVED_STATUS_VALUES:
        conflict_behavior = "QUESTIONABLE"

    if not candidates:
        raise ValueError("empty candidates")

    top = candidates[0]
    score_top = _score_claim(top, policy, now)
    resolved_status_top = _claim_status_to_resolved(top.status)
    winning_claim_id = str(top.claim_id)
    supporting: List[str] = [winning_claim_id]
    conflicting: List[str] = []

    if len(candidates) >= 2:
        second = candidates[1]
        score_second = _score_claim(second, policy, now)
        resolved_second = _claim_status_to_resolved(second.status)
        if resolved_status_top != resolved_second and abs(score_top - score_second) <= conflict_epsilon:
            resolved_status = conflict_behavior
            method = "UNRESOLVED_CONFLICT"
            resolution_confidence = _normalize_confidence(score_top, policy)
            conflicting = [str(c.claim_id) for c in candidates[1:]]
            supporting = [winning_claim_id]
        else:
            resolved_status = resolved_status_top
            method = "LATEST_WINS"
            resolution_confidence = _normalize_confidence(score_top, policy)
            for c in candidates[1:]:
                if _claim_status_to_resolved(c.status) != resolved_status:
                    conflicting.append(str(c.claim_id))
                else:
                    supporting.append(str(c.claim_id))
    else:
        resolved_status = resolved_status_top
        method = "LATEST_WINS"
        resolution_confidence = _normalize_confidence(score_top, policy)

    return {
        "fixture_id": None,
        "team_ref": top.team_ref,
        "player_ref": top.player_ref,
        "resolved_status": resolved_status,
        "resolution_confidence": resolution_confidence,
        "resolution_method": method,
        "winning_claim_id": winning_claim_id,
        "supporting_claim_ids": sorted(supporting),
        "conflicting_claim_ids": sorted(conflicting),
        "policy_version": policy_version,
        "created_at": now,
    }


async def _fetch_claims_with_report(
    session: AsyncSession,
    since_ts: datetime,
) -> List[_ClaimRow]:
    """Fetch all claims with report adapter_key, recorded_at, published_at (joined). Deterministic order by claim_id."""
    stmt = (
        select(
            InjuryNewsClaim.claim_id,
            InjuryNewsClaim.team_ref,
            InjuryNewsClaim.player_ref,
            InjuryNewsClaim.claim_type,
            InjuryNewsClaim.status,
            InjuryNewsClaim.confidence,
            InjuryNewsReport.adapter_key,
            InjuryNewsReport.recorded_at,
            InjuryNewsReport.published_at,
        )
        .join(InjuryNewsReport, InjuryNewsClaim.report_id == InjuryNewsReport.report_id)
        .where(InjuryNewsReport.recorded_at >= since_ts)
        .order_by(InjuryNewsClaim.claim_id)
    )
    result = await session.execute(stmt)
    rows: List[_ClaimRow] = []
    for r in result.all():
        rec_at = _ensure_utc(r.recorded_at) if r.recorded_at else r.recorded_at
        pub_at = _ensure_utc(r.published_at) if r.published_at else r.published_at
        rows.append(
            _ClaimRow(
                claim_id=r.claim_id,
                team_ref=r.team_ref,
                player_ref=r.player_ref,
                claim_type=r.claim_type,
                status=r.status,
                confidence=float(r.confidence),
                adapter_key=r.adapter_key,
                recorded_at=rec_at,
                published_at=pub_at,
            )
        )
    return rows


def _compute_since_ts(policy: Dict[str, Any], now: datetime) -> datetime:
    """Earliest recorded_at to consider (max of max_age_hours_by_claim_type)."""
    by_type = policy.get("max_age_hours_by_claim_type") or {}
    max_h = max((float(v) for v in by_type.values()), default=168.0)
    return now - timedelta(hours=max_h)


def run_resolver_pure(
    rows: List[_ClaimRow],
    policy: Dict[str, Any],
    now: datetime,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Pure resolver: filter, group, resolve. Returns (resolution_dicts, summary).
    summary: resolutions_count, conflicts_count, stale_dropped, low_conf_dropped, candidate_counts.
    """
    min_conf = float(policy.get("min_confidence_to_consider", 0.5))
    min_conf = max(0.0, min(1.0, min_conf))
    stale_dropped = 0
    low_conf_dropped = 0
    filtered: List[_ClaimRow] = []
    for r in rows:
        if r.confidence < min_conf:
            low_conf_dropped += 1
            continue
        if _is_stale(r, policy, now):
            stale_dropped += 1
            continue
        filtered.append(r)

    group_key = lambda r: (r.team_ref, r.player_ref if r.player_ref is not None else "__UNKNOWN_PLAYER__")
    groups: Dict[Tuple[str, Optional[str]], List[_ClaimRow]] = {}
    for r in filtered:
        k = (r.team_ref, r.player_ref)
        if k not in groups:
            groups[k] = []
        groups[k].append(r)

    resolutions: List[Dict[str, Any]] = []
    conflicts_count = 0
    for (team_ref, player_ref), cands in sorted(groups.items()):
        cands_sorted = sorted(
            cands,
            key=lambda r: (
                -_score_claim(r, policy, now),
                -(r.recorded_at.timestamp() if r.recorded_at else 0.0),
                r.claim_id,
            ),
        )
        res = _resolve_group(cands_sorted, policy, now)
        if res["resolution_method"] == "UNRESOLVED_CONFLICT":
            conflicts_count += 1
        resolutions.append(res)

    summary = {
        "resolutions_count": len(resolutions),
        "conflicts_count": conflicts_count,
        "stale_dropped": stale_dropped,
        "low_conf_dropped": low_conf_dropped,
        "candidate_counts": {"total": len(rows), "after_filter": len(filtered)},
    }
    return resolutions, summary


async def run_injury_news_resolver(
    session: AsyncSession,
    policy_version: str,
    fixture_id: Optional[str] = None,
    now_utc: Optional[datetime] = None,
) -> Dict[str, Any]:
    """
    Load policy, fetch claims, run pure resolver, delete previous resolutions for same (team_ref, player_ref, policy_version), persist new ones.
    Returns summary dict for report/ops (resolutions_count, conflicts_count, stale_dropped, low_conf_dropped, policy_version).
    """
    now = now_utc or datetime.now(timezone.utc)
    policy = load_policy(policy_version)
    since_ts = _compute_since_ts(policy, now)
    rows = await _fetch_claims_with_report(session, since_ts)
    candidate_counts = {"policy_version": policy_version, "candidates": len(rows)}

    from ops.ops_events import log_injury_news_resolve_start, log_injury_news_resolve_end
    scope = f"fixture:{fixture_id}" if fixture_id else "all"
    log_injury_news_resolve_start(policy_version, scope, len(rows))

    resolutions, summary = run_resolver_pure(rows, policy, now)
    summary["policy_version"] = policy_version
    if fixture_id is not None:
        for r in resolutions:
            r["fixture_id"] = fixture_id

    res_repo = InjuryNewsResolutionRepository(session)
    keys_to_replace = [(r["team_ref"], r["player_ref"]) for r in resolutions]
    if keys_to_replace:
        from sqlalchemy import and_, or_
        conds = or_(
            *[
                and_(
                    InjuryNewsResolution.team_ref == t,
                    InjuryNewsResolution.player_ref == p,
                )
                if p is not None
                else and_(
                    InjuryNewsResolution.team_ref == t,
                    InjuryNewsResolution.player_ref.is_(None),
                )
                for t, p in keys_to_replace
            ]
        )
        await session.execute(
            delete(InjuryNewsResolution).where(
                InjuryNewsResolution.policy_version == policy_version
            ).where(conds)
        )

    batch = []
    for r in sorted(resolutions, key=lambda x: (x["team_ref"], x["player_ref"] or "")):
        batch.append({
            **r,
            "supporting_claim_ids": r["supporting_claim_ids"],
            "conflicting_claim_ids": r["conflicting_claim_ids"],
        })
    if batch:
        await res_repo.save_resolutions(batch)

    log_injury_news_resolve_end(
        policy_version,
        summary["resolutions_count"],
        summary["conflicts_count"],
        summary["stale_dropped"],
        summary["low_conf_dropped"],
    )
    return summary
