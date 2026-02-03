"""
Deterministic checksums for ingestion payloads (provenance + dedup).
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from typing import Any, Dict, List

from ingestion.schema import IngestedMatchData, OddsSnapshot


def stable_json_dumps(obj: Any) -> str:
    """Serialize to JSON with sorted keys for deterministic output."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), default=_json_default)


def _json_default(o: Any) -> Any:
    if isinstance(o, datetime):
        return o.isoformat()
    raise TypeError(f"Object of type {type(o).__name__} is not JSON serializable")


def sha256_hex(text: str) -> str:
    """Return SHA-256 hash of text as hex string."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def odds_checksum(snapshot: OddsSnapshot) -> str:
    """Deterministic checksum of stable OddsSnapshot fields (market, selection, odds, source, collected_at_utc)."""
    stable: Dict[str, Any] = {
        "market": snapshot.market,
        "selection": snapshot.selection,
        "odds": snapshot.odds,
        "source": snapshot.source,
        "collected_at_utc": snapshot.collected_at_utc.isoformat() if snapshot.collected_at_utc else None,
    }
    return sha256_hex(stable_json_dumps(stable))


def ingested_checksum(data: IngestedMatchData) -> str:
    """Deterministic checksum of identity + odds checksums + state (no source/collected_at/checksum)."""
    identity_json = data.identity.model_dump(mode="json")
    odds_checksums: List[str] = [odds_checksum(o) for o in data.odds]
    state_json: Any = data.state.model_dump(mode="json") if data.state else None
    payload = {
        "identity": identity_json,
        "odds_checksums": sorted(odds_checksums),
        "state": state_json,
    }
    return sha256_hex(stable_json_dumps(payload))
