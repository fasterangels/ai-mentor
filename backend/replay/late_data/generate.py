"""
Late-data variant generator (I1 Part A).
Pure, deterministic: base envelope + parameters -> derived envelope (timing only).
Payload untouched; envelope_checksum changes; payload_checksum unchanged.
"""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Tuple

from pipeline.snapshot_envelope import (
    compute_envelope_checksum,
    compute_payload_checksum,
)

from replay.late_data.model import ReplayScenario, ScenarioType

# Fixed delay offsets for DELAYED_OBSERVED_AT (minutes)
DELAY_OFFSET_MINUTES: Tuple[int, ...] = (15, 60, 6 * 60, 24 * 60, 3 * 24 * 60)  # 15m, 1h, 6h, 24h, 3d

# Optional timing fields that may be dropped for MISSING_TIMING_TAGS
OPTIONAL_TIMING_KEYS: Tuple[str, ...] = (
    "fetch_started_at_utc",
    "fetch_ended_at_utc",
    "latency_ms",
    "effective_from_utc",
    "expected_valid_until_utc",
)

# Fixed effective_from shift offsets in minutes (negative = earlier)
STALE_EFFECTIVE_OFFSET_MINUTES: Tuple[int, ...] = (-60, 60, 6 * 60)  # -1h, +1h, +6h


def _parse_iso(s: str) -> datetime | None:
    if not s or not s.strip():
        return None
    s = s.strip().replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except ValueError:
        return None


def _iso_str(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat()


def _scenario_id_slug(base_snapshot_id: str, scenario_type: ScenarioType, parameters: Dict[str, Any]) -> str:
    """Deterministic scenario_id from base id, type, and params."""
    parts = [base_snapshot_id, scenario_type.value]
    for k in sorted(parameters.keys()):
        v = parameters[k]
        parts.append(f"{k}={v}")
    raw = "__".join(str(p) for p in parts)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def apply_delayed_observed_at(meta: Dict[str, Any], delay_minutes: int) -> Dict[str, Any]:
    """Return new metadata with observed_at_utc moved later by delay_minutes. Copy; do not mutate input."""
    out = deepcopy(meta)
    observed = out.get("observed_at_utc") or out.get("created_at_utc") or ""
    dt = _parse_iso(observed)
    if dt is None:
        return out
    out["observed_at_utc"] = _iso_str(dt + timedelta(minutes=delay_minutes))
    return out


def apply_missing_timing_tags(meta: Dict[str, Any]) -> Dict[str, Any]:
    """Return new metadata with optional timing fields removed. Copy; do not mutate input."""
    out = deepcopy(meta)
    for key in OPTIONAL_TIMING_KEYS:
        out.pop(key, None)
    return out


def apply_stale_effective_from(meta: Dict[str, Any], shift_minutes: int) -> Dict[str, Any]:
    """Return new metadata with effective_from_utc shifted. If missing, use observed_at_utc as base. Copy."""
    out = deepcopy(meta)
    base_ts = out.get("effective_from_utc") or out.get("observed_at_utc") or out.get("created_at_utc") or ""
    dt = _parse_iso(base_ts)
    if dt is None:
        return out
    out["effective_from_utc"] = _iso_str(dt + timedelta(minutes=shift_minutes))
    return out


def build_scenario_block(
    scenario_id: str,
    base_snapshot_id: str,
    fixture_id: str,
    scenario_type: ScenarioType,
    parameters: Dict[str, Any],
    created_at_utc: str,
) -> Dict[str, Any]:
    """Build the scenario block to inject into envelope metadata."""
    return {
        "scenario_id": scenario_id,
        "base_snapshot_id": base_snapshot_id,
        "fixture_id": fixture_id,
        "scenario_type": scenario_type.value,
        "parameters": parameters,
        "created_at_utc": created_at_utc,
    }


def generate_variant_metadata(
    base_meta: Dict[str, Any],
    payload: Dict[str, Any],
    scenario_type: ScenarioType,
    parameters: Dict[str, Any],
    fixture_id: str,
    created_at_utc: str,
) -> Tuple[ReplayScenario, Dict[str, Any]]:
    """
    Pure: from base envelope metadata and payload, produce (ReplayScenario, derived_metadata).
    Payload is not modified. payload_checksum in derived_metadata must equal base; envelope_checksum will differ.
    """
    base_snapshot_id = base_meta.get("snapshot_id") or base_meta.get("payload_checksum") or ""
    scenario_id = _scenario_id_slug(base_snapshot_id, scenario_type, parameters)

    if scenario_type == ScenarioType.DELAYED_OBSERVED_AT:
        delay_min = int(parameters.get("delay_minutes", 0))
        derived = apply_delayed_observed_at(base_meta, delay_min)
    elif scenario_type == ScenarioType.MISSING_TIMING_TAGS:
        derived = apply_missing_timing_tags(base_meta)
    elif scenario_type == ScenarioType.STALE_EFFECTIVE_FROM:
        shift_min = int(parameters.get("shift_minutes", 0))
        derived = apply_stale_effective_from(base_meta, shift_min)
    else:
        derived = deepcopy(base_meta)

    # Preserve payload_checksum (payload unchanged)
    derived["payload_checksum"] = base_meta.get("payload_checksum") or compute_payload_checksum(payload)

    # Inject scenario block
    derived["scenario"] = build_scenario_block(
        scenario_id=scenario_id,
        base_snapshot_id=base_snapshot_id,
        fixture_id=fixture_id,
        scenario_type=scenario_type,
        parameters=parameters,
        created_at_utc=created_at_utc,
    )

    # Recompute envelope checksum (exclude envelope_checksum then set it)
    derived.pop("envelope_checksum", None)
    derived["envelope_checksum"] = compute_envelope_checksum(derived)

    scenario = ReplayScenario(
        scenario_id=scenario_id,
        base_snapshot_id=base_snapshot_id,
        fixture_id=fixture_id,
        scenario_type=scenario_type,
        parameters=parameters,
        created_at_utc=created_at_utc,
    )
    return scenario, derived


def generate_delayed_observed_at_scenarios(
    base_meta: Dict[str, Any],
    payload: Dict[str, Any],
    fixture_id: str,
    created_at_utc: str,
) -> List[Tuple[ReplayScenario, Dict[str, Any]]]:
    """Generate one variant per fixed delay offset. Deterministic order."""
    out: List[Tuple[ReplayScenario, Dict[str, Any]]] = []
    for delay_min in DELAY_OFFSET_MINUTES:
        scenario, derived = generate_variant_metadata(
            base_meta, payload, ScenarioType.DELAYED_OBSERVED_AT, {"delay_minutes": delay_min}, fixture_id, created_at_utc
        )
        out.append((scenario, derived))
    return out


def generate_missing_timing_tags_scenario(
    base_meta: Dict[str, Any],
    payload: Dict[str, Any],
    fixture_id: str,
    created_at_utc: str,
) -> Tuple[ReplayScenario, Dict[str, Any]]:
    """Generate single MISSING_TIMING_TAGS variant."""
    return generate_variant_metadata(
        base_meta, payload, ScenarioType.MISSING_TIMING_TAGS, {}, fixture_id, created_at_utc
    )


def generate_stale_effective_from_scenarios(
    base_meta: Dict[str, Any],
    payload: Dict[str, Any],
    fixture_id: str,
    created_at_utc: str,
) -> List[Tuple[ReplayScenario, Dict[str, Any]]]:
    """Generate one variant per fixed effective_from shift. Deterministic order."""
    out: List[Tuple[ReplayScenario, Dict[str, Any]]] = []
    for shift_min in STALE_EFFECTIVE_OFFSET_MINUTES:
        scenario, derived = generate_variant_metadata(
            base_meta, payload, ScenarioType.STALE_EFFECTIVE_FROM, {"shift_minutes": shift_min}, fixture_id, created_at_utc
        )
        out.append((scenario, derived))
    return out


def derived_payload_json(metadata: Dict[str, Any], payload: Dict[str, Any]) -> str:
    """Build full payload_json string { metadata, payload } for storage."""
    return json.dumps({"metadata": metadata, "payload": payload}, sort_keys=True, separators=(",", ":"), default=str)
