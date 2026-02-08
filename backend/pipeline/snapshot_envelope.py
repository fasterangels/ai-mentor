"""
Canonical SnapshotEnvelope (G2): provenance and timing tags for all snapshots.
Backward compatible: legacy payload_json without envelope is read with safe defaults.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

# Schema version for new envelopes
ENVELOPE_SCHEMA_VERSION = 1

# Source class and reliability tier literals (use as strings in JSON)
SOURCE_CLASS_RECORDED = "RECORDED"
SOURCE_CLASS_LIVE_SHADOW = "LIVE_SHADOW"
SOURCE_CLASS_EDITORIAL = "EDITORIAL"
SOURCE_CLASS_UNKNOWN = "UNKNOWN"

RELIABILITY_TIER_HIGH = "HIGH"
RELIABILITY_TIER_MED = "MED"
RELIABILITY_TIER_LOW = "LOW"


def _canonical_json(obj: Any) -> str:
    """Stable JSON for hashing (sorted keys, no extra whitespace)."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str)


def compute_payload_checksum(raw_payload: Dict[str, Any] | str) -> str:
    """SHA-256 of canonical payload. Accepts dict or already-serialized string."""
    if isinstance(raw_payload, str):
        try:
            raw_payload = json.loads(raw_payload)
        except json.JSONDecodeError:
            return hashlib.sha256(raw_payload.encode("utf-8")).hexdigest()
    return hashlib.sha256(_canonical_json(raw_payload).encode("utf-8")).hexdigest()


def _envelope_for_checksum(meta: Dict[str, Any]) -> Dict[str, Any]:
    """Copy metadata without envelope_checksum for integrity computation."""
    out = {k: v for k, v in meta.items() if k != "envelope_checksum"}
    return out


def compute_envelope_checksum(metadata: Dict[str, Any]) -> str:
    """SHA-256 of canonicalized envelope metadata (excluding envelope_checksum)."""
    clean = _envelope_for_checksum(metadata)
    return hashlib.sha256(_canonical_json(clean).encode("utf-8")).hexdigest()


def _iso(dt: Optional[datetime]) -> Optional[str]:
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat()


@dataclass
class SnapshotSource:
    class_: str  # RECORDED | LIVE_SHADOW | EDITORIAL | UNKNOWN
    name: str
    ref: Optional[str] = None
    reliability_tier: str = RELIABILITY_TIER_MED

    def to_dict(self) -> Dict[str, Any]:
        return {
            "class": self.class_,
            "name": self.name,
            "ref": self.ref,
            "reliability_tier": self.reliability_tier,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "SnapshotSource":
        return cls(
            class_=str(d.get("class", SOURCE_CLASS_UNKNOWN)),
            name=str(d.get("name", "unknown")),
            ref=d.get("ref"),
            reliability_tier=str(d.get("reliability_tier", RELIABILITY_TIER_MED)),
        )


@dataclass
class SnapshotEnvelope:
    """Canonical envelope v1. All UTC timestamps as ISO strings in JSON."""

    snapshot_id: str
    snapshot_type: str  # "recorded" | "live_shadow" | etc.
    created_at_utc: str
    payload_checksum: str
    source: SnapshotSource
    observed_at_utc: str
    fetch_started_at_utc: Optional[str] = None
    fetch_ended_at_utc: Optional[str] = None
    latency_ms: Optional[float] = None
    effective_from_utc: Optional[str] = None
    expected_valid_until_utc: Optional[str] = None
    schema_version: int = ENVELOPE_SCHEMA_VERSION
    envelope_checksum: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "snapshot_id": self.snapshot_id,
            "snapshot_type": self.snapshot_type,
            "created_at_utc": self.created_at_utc,
            "payload_checksum": self.payload_checksum,
            "source": self.source.to_dict(),
            "observed_at_utc": self.observed_at_utc,
            "schema_version": self.schema_version,
        }
        if self.fetch_started_at_utc is not None:
            d["fetch_started_at_utc"] = self.fetch_started_at_utc
        if self.fetch_ended_at_utc is not None:
            d["fetch_ended_at_utc"] = self.fetch_ended_at_utc
        if self.latency_ms is not None:
            d["latency_ms"] = round(self.latency_ms, 2)
        if self.effective_from_utc is not None:
            d["effective_from_utc"] = self.effective_from_utc
        if self.expected_valid_until_utc is not None:
            d["expected_valid_until_utc"] = self.expected_valid_until_utc
        if self.envelope_checksum is not None:
            d["envelope_checksum"] = self.envelope_checksum
        return d

    def with_envelope_checksum(self) -> "SnapshotEnvelope":
        """Return a copy with envelope_checksum computed (excludes envelope_checksum from input)."""
        d = self.to_dict()
        d.pop("envelope_checksum", None)
        checksum = compute_envelope_checksum(d)
        return SnapshotEnvelope(
            snapshot_id=self.snapshot_id,
            snapshot_type=self.snapshot_type,
            created_at_utc=self.created_at_utc,
            payload_checksum=self.payload_checksum,
            source=self.source,
            observed_at_utc=self.observed_at_utc,
            fetch_started_at_utc=self.fetch_started_at_utc,
            fetch_ended_at_utc=self.fetch_ended_at_utc,
            latency_ms=self.latency_ms,
            effective_from_utc=self.effective_from_utc,
            expected_valid_until_utc=self.expected_valid_until_utc,
            schema_version=self.schema_version,
            envelope_checksum=checksum,
        )


def build_envelope_for_recorded(
    payload: Dict[str, Any],
    snapshot_id: str,
    created_at_utc: datetime,
    source_name: str = "recorded",
) -> SnapshotEnvelope:
    """Build envelope for recorded snapshots. observed_at_utc defaults to created_at_utc."""
    created_str = _iso(created_at_utc) or datetime.now(timezone.utc).isoformat()
    payload_checksum = compute_payload_checksum(payload)
    env = SnapshotEnvelope(
        snapshot_id=snapshot_id,
        snapshot_type="recorded",
        created_at_utc=created_str,
        payload_checksum=payload_checksum,
        source=SnapshotSource(
            class_=SOURCE_CLASS_RECORDED,
            name=source_name,
            ref=None,
            reliability_tier=RELIABILITY_TIER_HIGH,
        ),
        observed_at_utc=created_str,
        schema_version=ENVELOPE_SCHEMA_VERSION,
    )
    return env.with_envelope_checksum()


def build_envelope_for_live_shadow(
    payload: Dict[str, Any],
    snapshot_id: str,
    created_at_utc: datetime,
    source_name: str,
    observed_at_utc: datetime,
    fetch_started_at_utc: Optional[datetime] = None,
    fetch_ended_at_utc: Optional[datetime] = None,
    latency_ms: Optional[float] = None,
) -> SnapshotEnvelope:
    """Build envelope for live_shadow snapshots with timing tags."""
    created_str = _iso(created_at_utc) or datetime.now(timezone.utc).isoformat()
    observed_str = _iso(observed_at_utc) or created_str
    payload_checksum = compute_payload_checksum(payload)
    env = SnapshotEnvelope(
        snapshot_id=snapshot_id,
        snapshot_type="live_shadow",
        created_at_utc=created_str,
        payload_checksum=payload_checksum,
        source=SnapshotSource(
            class_=SOURCE_CLASS_LIVE_SHADOW,
            name=source_name,
            ref=None,
            reliability_tier=RELIABILITY_TIER_MED,
        ),
        observed_at_utc=observed_str,
        fetch_started_at_utc=_iso(fetch_started_at_utc) if fetch_started_at_utc else None,
        fetch_ended_at_utc=_iso(fetch_ended_at_utc) if fetch_ended_at_utc else None,
        latency_ms=latency_ms,
        schema_version=ENVELOPE_SCHEMA_VERSION,
    )
    return env.with_envelope_checksum()


def _parse_iso(s: str) -> Optional[datetime]:
    """Parse ISO timestamp; accept Z or +00:00 for UTC."""
    if not s:
        return None
    s = s.strip().replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(s)
    except ValueError:
        return None


def compute_latency_ms(fetch_started_at_utc: Optional[str], fetch_ended_at_utc: Optional[str]) -> Optional[float]:
    """Compute latency_ms from ISO timestamp strings. Returns None if either missing."""
    if not fetch_started_at_utc or not fetch_ended_at_utc:
        return None
    start = _parse_iso(fetch_started_at_utc)
    end = _parse_iso(fetch_ended_at_utc)
    if start is None or end is None:
        return None
    return (end - start).total_seconds() * 1000


def parse_payload_json(
    payload_json: str,
    created_at_utc_fallback: Optional[datetime] = None,
    on_missing_fields: Optional[Any] = None,
    on_integrity_failed: Optional[Any] = None,
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Parse payload_json from storage. Returns (metadata_dict, payload_dict).
    - If format is envelope (has "metadata" and "payload"): returns (metadata, payload).
      Fills missing envelope fields with defaults and optionally calls on_missing_fields(missing_keys).
    - If legacy (no envelope): builds default metadata and returns (default_metadata, parsed_json).
    Never raises for missing new fields; defaults applied.
    """
    try:
        raw = json.loads(payload_json)
    except json.JSONDecodeError:
        created = created_at_utc_fallback or datetime.now(timezone.utc)
        created_str = created.isoformat()
        default_meta = {
            "snapshot_id": "",
            "snapshot_type": "recorded",
            "created_at_utc": created_str,
            "payload_checksum": "",
            "source": {"class": SOURCE_CLASS_RECORDED, "name": "recorded", "ref": None, "reliability_tier": RELIABILITY_TIER_HIGH},
            "observed_at_utc": created_str,
            "schema_version": 0,
        }
        if on_missing_fields:
            on_missing_fields(["legacy_no_envelope"])
        return default_meta, {}
    if isinstance(raw, dict) and "metadata" in raw and "payload" in raw:
        meta = dict(raw["metadata"])
        payload = raw["payload"] if isinstance(raw["payload"], dict) else {}
        created_fallback = created_at_utc_fallback or datetime.now(timezone.utc)
        created_str = created_fallback.isoformat()
        missing: List[str] = []
        # Normalize G1-style keys to G2 names
        if meta.get("observed_at") and not meta.get("observed_at_utc"):
            meta["observed_at_utc"] = meta["observed_at"]
        if meta.get("checksum") and not meta.get("payload_checksum"):
            meta["payload_checksum"] = meta["checksum"]
        if meta.get("fetch_started_at") and not meta.get("fetch_started_at_utc"):
            meta["fetch_started_at_utc"] = meta["fetch_started_at"]
        if meta.get("fetch_ended_at") and not meta.get("fetch_ended_at_utc"):
            meta["fetch_ended_at_utc"] = meta["fetch_ended_at"]
        if not meta.get("created_at_utc"):
            meta["created_at_utc"] = meta.get("created_at") or created_str
            if not meta.get("created_at"):
                missing.append("created_at_utc")
        if not meta.get("observed_at_utc"):
            meta["observed_at_utc"] = meta.get("created_at_utc") or created_str
            missing.append("observed_at_utc")
        if "schema_version" not in meta:
            meta["schema_version"] = 0
            missing.append("schema_version")
        if not meta.get("source") or not isinstance(meta["source"], dict):
            meta["source"] = {"class": SOURCE_CLASS_RECORDED, "name": "recorded", "ref": None, "reliability_tier": RELIABILITY_TIER_HIGH}
            missing.append("source")
        if "snapshot_id" not in meta or meta["snapshot_id"] == "":
            meta["snapshot_id"] = meta.get("payload_checksum") or meta.get("checksum") or ""
        if missing and on_missing_fields:
            on_missing_fields(missing)
        stored_checksum = meta.get("envelope_checksum")
        if stored_checksum and on_integrity_failed:
            computed = compute_envelope_checksum(meta)
            if computed != stored_checksum:
                on_integrity_failed(meta.get("snapshot_id", ""), "envelope_checksum mismatch")
        return meta, payload
    # Legacy: whole thing is payload
    created = created_at_utc_fallback or datetime.now(timezone.utc)
    created_str = created.isoformat()
    default_meta = {
        "snapshot_id": "",
        "snapshot_type": "recorded",
        "created_at_utc": created_str,
        "payload_checksum": "",
        "source": {"class": SOURCE_CLASS_RECORDED, "name": "recorded", "ref": None, "reliability_tier": RELIABILITY_TIER_HIGH},
        "observed_at_utc": created_str,
        "schema_version": 0,
    }
    if on_missing_fields:
        on_missing_fields(["legacy_no_envelope"])
    return default_meta, raw if isinstance(raw, dict) else {}
