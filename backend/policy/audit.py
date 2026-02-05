"""Decision audit: current vs proposed policy per snapshot."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from policy.policy_model import Policy
from policy.policy_runtime import min_confidence_from_policy
from policy.policy_store import checksum_report

MARKETS_V2 = ["1X2", "OU_2.5", "BTTS"]
MARKET_TO_POLICY_KEY = {"1X2": "one_x_two", "OU_2.5": "over_under_25", "BTTS": "gg_ng"}


@dataclass
class AuditRow:
    snapshot_id: str
    market: str
    before_pick: str
    after_pick: str
    before_confidence: float | None
    after_confidence: float | None
    changed: bool
    change_reason: str
    reasons_added: list[str]
    reasons_removed: list[str]


def _pick_from_decision(d: dict) -> str:
    kind = d.get("decision") or "NO_PREDICTION"
    if kind == "PLAY":
        sel = d.get("selection")
        return str(sel) if sel is not None else "PLAY"
    return kind


def _reasons_from_decision(d: dict) -> list[str]:
    return list(d.get("reasons") or [])


def _infer_change_reason(before_pick: str, after_pick: str, min_current: float, min_proposed: float) -> str:
    if before_pick == after_pick:
        return ""
    if min_proposed > min_current:
        if before_pick == "PLAY" and after_pick in ("NO_BET", "NO_PREDICTION"):
            return "min_confidence_gate"
        if before_pick == "NO_BET" and after_pick == "NO_PREDICTION":
            return "min_confidence_gate"
    if min_proposed < min_current and after_pick == "PLAY" and before_pick in ("NO_BET", "NO_PREDICTION"):
        return "min_confidence_relaxed"
    return "policy_change"


def audit_snapshots(
    snapshots: list[dict[str, Any]],
    current_policy: Policy,
    proposed_policy: Policy,
) -> dict[str, Any]:
    from evaluation.evaluation_v2 import evidence_pack_from_dict
    from analyzer.v2.engine import analyze_v2

    min_current = min_confidence_from_policy(current_policy)
    min_proposed = min_confidence_from_policy(proposed_policy)
    rows: list[AuditRow] = []

    for item in snapshots:
        snapshot_id = item.get("match_id") or "unknown"
        ep_dict = item.get("evidence_pack")
        if not ep_dict:
            continue
        try:
            ep = evidence_pack_from_dict(ep_dict)
        except Exception:
            continue
        out_before = analyze_v2("RESOLVED", ep, MARKETS_V2, min_confidence=min_current)
        out_after = analyze_v2("RESOLVED", ep, MARKETS_V2, min_confidence=min_proposed)
        decisions_before = {d.get("market"): d for d in (out_before.get("decisions") or [])}
        decisions_after = {d.get("market"): d for d in (out_after.get("decisions") or [])}

        for market_id in MARKETS_V2:
            policy_key = MARKET_TO_POLICY_KEY.get(market_id, market_id.lower())
            d_before = decisions_before.get(market_id)
            d_after = decisions_after.get(market_id)
            before_pick = _pick_from_decision(d_before) if d_before else "NO_PREDICTION"
            after_pick = _pick_from_decision(d_after) if d_after else "NO_PREDICTION"
            before_conf = float(d_before["confidence"]) if d_before and d_before.get("confidence") is not None else None
            after_conf = float(d_after["confidence"]) if d_after and d_after.get("confidence") is not None else None
            changed = before_pick != after_pick or (before_conf != after_conf and (before_conf is not None or after_conf is not None))
            change_reason = _infer_change_reason(before_pick, after_pick, min_current, min_proposed) if changed else ""
            reasons_before = set(_reasons_from_decision(d_before)) if d_before else set()
            reasons_after = set(_reasons_from_decision(d_after)) if d_after else set()
            rows.append(AuditRow(
                snapshot_id=snapshot_id,
                market=policy_key,
                before_pick=before_pick,
                after_pick=after_pick,
                before_confidence=before_conf,
                after_confidence=after_conf,
                changed=changed,
                change_reason=change_reason,
                reasons_added=sorted(reasons_after - reasons_before),
                reasons_removed=sorted(reasons_before - reasons_after),
            ))

    total = len(rows)
    changed_count = sum(1 for r in rows if r.changed)
    per_market_changes: dict[str, int] = {}
    for r in rows:
        per_market_changes[r.market] = per_market_changes.get(r.market, 0) + (1 if r.changed else 0)

    snapshots_checksum = checksum_report({"snapshots_count": len(snapshots), "match_ids": [s.get("match_id") for s in snapshots]})
    current_checksum = checksum_report(current_policy.model_dump(mode="json"))
    proposed_dump = proposed_policy.model_dump(mode="json")
    if "meta" in proposed_dump and isinstance(proposed_dump["meta"], dict):
        proposed_dump = {**proposed_dump, "meta": {k: v for k, v in proposed_dump["meta"].items() if k != "created_at_utc"}}
    proposed_checksum = checksum_report(proposed_dump)

    return {
        "summary": {"total_markets": total, "changed_count": changed_count, "unchanged_count": total - changed_count, "per_market_change_count": per_market_changes},
        "rows": [{"snapshot_id": r.snapshot_id, "market": r.market, "before_pick": r.before_pick, "after_pick": r.after_pick, "before_confidence": r.before_confidence, "after_confidence": r.after_confidence, "changed": r.changed, "change_reason": r.change_reason, "reasons_added": r.reasons_added, "reasons_removed": r.reasons_removed} for r in rows],
        "snapshots_checksum": snapshots_checksum,
        "current_policy_checksum": current_checksum,
        "proposed_policy_checksum": proposed_checksum,
    }
