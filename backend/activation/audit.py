"""
Activation Audit: records of activation decisions for audit trail.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from activation.gate import get_activation_config


async def create_activation_audit(
    session: AsyncSession,
    connector_name: str,
    match_id: str,
    market: str,
    decision: Dict[str, Any],
    confidence: float,
    reasons: List[str],
    activation_allowed: bool,
    activation_reason: Optional[str] = None,
    guardrail_state: Optional[Dict[str, Any]] = None,
    *,
    now_utc: Optional[datetime] = None,
) -> Dict[str, Any]:
    """
    Create an activation audit record.
    Returns audit dict (for reporting); does not persist to DB yet.
    """
    now = now_utc or datetime.now(timezone.utc)
    config = get_activation_config()
    
    audit = {
        "created_at_utc": now.isoformat(),
        "connector_name": connector_name,
        "match_id": match_id,
        "market": market,
        "decision": decision,
        "confidence": confidence,
        "reasons": reasons,
        "activation_allowed": activation_allowed,
        "activation_reason": activation_reason,
        "activation_config": config,
        "guardrail_state": guardrail_state or {},
    }
    
    return audit


async def persist_activation_audit(
    session: AsyncSession,
    audit: Dict[str, Any],
) -> None:
    """
    Persist activation audit record to database.
    For now, we'll store in a simple table or JSON file.
    In production, this would be a proper DB table.
    """
    # TODO: Implement proper DB persistence
    # For now, we'll include audit in reports/index.json
    pass


def build_activation_summary(
    audits: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Build activation summary from audit records.
    """
    total = len(audits)
    activated = sum(1 for a in audits if a.get("activation_allowed"))
    not_activated = total - activated
    
    reasons: Dict[str, int] = {}
    for audit in audits:
        reason = audit.get("activation_reason") or "unknown"
        reasons[reason] = reasons.get(reason, 0) + 1
    
    return {
        "total_decisions": total,
        "activated": activated,
        "not_activated": not_activated,
        "activation_rate": activated / total if total > 0 else 0.0,
        "reasons": reasons,
    }
