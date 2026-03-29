"""
Recorded injury/news adapter: reads local JSON fixtures, persists reports and claims.
No network; deterministic. Adapter key: recorded_injury_news_v1.
"""

from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from ingestion.checksums import sha256_hex
from repositories.injury_news_claim_repo import InjuryNewsClaimRepository
from repositories.injury_news_report_repo import InjuryNewsReportRepository

ADAPTER_KEY = "recorded_injury_news_v1"

CLAIM_TYPE_VALUES = frozenset({"INJURY_STATUS", "SUSPENSION", "RETURN"})
STATUS_VALUES = frozenset({"OUT", "DOUBTFUL", "FIT", "SUSPENDED", "UNKNOWN"})
VALIDITY_VALUES = frozenset({"NEXT_MATCH", "DATE", "RANGE", "UNKNOWN"})


def _artifact_checksum(path: Path) -> str:
    """SHA-256 of raw file bytes (deterministic)."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _stable_json_dumps(obj: Any) -> str:
    """Deterministic JSON (sorted keys, no trailing whitespace)."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), default=_json_default)


def _json_default(o: Any) -> Any:
    if isinstance(o, datetime):
        return o.isoformat()
    raise TypeError(f"Object of type {type(o).__name__} is not JSON serializable")


def _parse_optional_datetime(value: Any) -> Optional[datetime]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if not isinstance(value, str) or not value.strip():
        return None
    s = value.strip().replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(s)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _normalize_claim(raw: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize one claim: trim strings, enforce enums, clamp confidence. Fail-fast on invalid enum."""
    team_ref = (raw.get("team_ref") or "").strip()
    if not team_ref:
        raise ValueError("claim.team_ref is required and must be non-empty")
    player_ref = raw.get("player_ref")
    player_ref = player_ref.strip() if isinstance(player_ref, str) else None
    if player_ref == "":
        player_ref = None

    claim_type = (raw.get("claim_type") or "").strip().upper()
    if claim_type not in CLAIM_TYPE_VALUES:
        raise ValueError(f"claim.claim_type must be one of {sorted(CLAIM_TYPE_VALUES)}, got {claim_type!r}")
    status = (raw.get("status") or "").strip().upper()
    if status not in STATUS_VALUES:
        raise ValueError(f"claim.status must be one of {sorted(STATUS_VALUES)}, got {status!r}")
    validity = (raw.get("validity") or "").strip().upper()
    if validity not in VALIDITY_VALUES:
        raise ValueError(f"claim.validity must be one of {sorted(VALIDITY_VALUES)}, got {validity!r}")

    try:
        confidence = float(raw.get("confidence", 0.0))
    except (TypeError, ValueError):
        raise ValueError("claim.confidence must be a number")
    confidence = max(0.0, min(1.0, confidence))

    valid_from = _parse_optional_datetime(raw.get("valid_from"))
    valid_to = _parse_optional_datetime(raw.get("valid_to"))
    evidence_ptr = raw.get("evidence_ptr")
    if evidence_ptr is not None and not isinstance(evidence_ptr, str):
        evidence_ptr = json.dumps(evidence_ptr, sort_keys=True)

    return {
        "team_ref": team_ref,
        "player_ref": player_ref,
        "claim_type": claim_type,
        "status": status,
        "validity": validity,
        "valid_from": valid_from,
        "valid_to": valid_to,
        "confidence": confidence,
        "evidence_ptr": evidence_ptr,
    }


def _normalize_report(raw: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize report: source_ref, published_at, title, body, claims (list of normalized claims)."""
    source_ref = raw.get("source_ref")
    source_ref = source_ref.strip() if isinstance(source_ref, str) else None
    published_at = _parse_optional_datetime(raw.get("published_at"))
    title = raw.get("title")
    title = title.strip() if isinstance(title, str) else None
    if title == "":
        title = None
    body = raw.get("body")
    body = body.strip() if isinstance(body, str) else None
    if body == "":
        body = None

    claims_raw = raw.get("claims")
    if not isinstance(claims_raw, list):
        raise ValueError("report.claims must be an array")
    claims = [_normalize_claim(c) for c in claims_raw]

    return {
        "source_ref": source_ref,
        "published_at": published_at,
        "title": title,
        "body": body,
        "claims": claims,
    }


def _content_checksum(normalized: Dict[str, Any]) -> str:
    """Stable checksum of normalized report (for dedupe)."""
    # Build JSON-serializable payload (datetimes -> isoformat)
    claims_ser: List[Dict[str, Any]] = []
    for c in normalized["claims"]:
        cc = {k: v for k, v in c.items() if v is not None}
        if "valid_from" in cc and hasattr(cc["valid_from"], "isoformat"):
            cc["valid_from"] = cc["valid_from"].isoformat()
        if "valid_to" in cc and hasattr(cc["valid_to"], "isoformat"):
            cc["valid_to"] = cc["valid_to"].isoformat()
        claims_ser.append(cc)
    published = normalized.get("published_at")
    payload = {
        "source_ref": normalized.get("source_ref"),
        "published_at": published.isoformat() if published else None,
        "title": normalized.get("title"),
        "body": normalized.get("body"),
        "claims": claims_ser,
    }
    return sha256_hex(_stable_json_dumps(payload))


def _injury_news_fixtures_dir() -> Path:
    """Default fixtures directory for injury/news (no network; local only)."""
    base = Path(__file__).resolve().parent
    return base / "fixtures" / "injury_news"


def load_injury_news_fixtures(fixtures_dir: Optional[Path] = None) -> List[tuple[Path, Dict[str, Any]]]:
    """
    Load all JSON artifacts from fixtures dir. Returns list of (path, normalized_content).
    Deterministic: files sorted by path. Raises ValueError on invalid enum/content.
    No network; reads local paths only.
    """
    directory = Path(fixtures_dir) if fixtures_dir else _injury_news_fixtures_dir()
    if not directory.is_dir():
        return []
    results: List[tuple[Path, Dict[str, Any]]] = []
    for path in sorted(directory.glob("*.json")):
        try:
            text = path.read_text(encoding="utf-8")
            raw = json.loads(text)
        except (OSError, json.JSONDecodeError) as e:
            raise ValueError(f"Invalid fixture {path}: {e}") from e
        if not isinstance(raw, dict):
            raise ValueError(f"Fixture {path} must be a JSON object")
        normalized = _normalize_report(raw)
        results.append((path, normalized))
    return results


async def run_recorded_injury_news_ingestion(
    session: AsyncSession,
    fixtures_dir: Optional[Path] = None,
    now_utc: Optional[datetime] = None,
    adapter_key: str = ADAPTER_KEY,
) -> int:
    """
    Read injury/news fixtures from fixtures_dir (or default), persist reports and claims.
    Returns number of reports processed. No network; local files only.
    recorded_at and created_at use now_utc (injectable for tests).
    """
    now = now_utc or datetime.now(timezone.utc)
    report_repo = InjuryNewsReportRepository(session)
    claim_repo = InjuryNewsClaimRepository(session)
    count = 0
    for path, normalized in load_injury_news_fixtures(fixtures_dir):
        artifact_checksum = _artifact_checksum(path)
        content_checksum = _content_checksum(normalized)
        existing = await report_repo.find_by_content_checksum_and_adapter(
            content_checksum, adapter_key
        )
        if existing:
            continue
        report_id = f"inj_{content_checksum[:24]}"
        body_excerpt = normalized.get("body")
        title = normalized.get("title")

        await report_repo.upsert_report(
            report_id=report_id,
            adapter_key=adapter_key,
            artifact_path=str(path),
            artifact_checksum=artifact_checksum,
            content_checksum=content_checksum,
            recorded_at=now,
            created_at=now,
            source_ref=normalized.get("source_ref"),
            published_at=normalized.get("published_at"),
            title=title,
            body_excerpt=body_excerpt,
        )
        await session.flush()

        claims_for_db: List[dict] = []
        for c in normalized["claims"]:
            claims_for_db.append({
                "team_ref": c["team_ref"],
                "player_ref": c.get("player_ref"),
                "claim_type": c["claim_type"],
                "status": c["status"],
                "validity": c["validity"],
                "valid_from": c.get("valid_from"),
                "valid_to": c.get("valid_to"),
                "confidence": c["confidence"],
                "evidence_ptr": c.get("evidence_ptr"),
            })
        await claim_repo.add_claims(report_id=report_id, claims=claims_for_db, created_at=now)
        count += 1
    return count


def inj_news_enabled() -> bool:
    """True if INJ_NEWS_ENABLED is set to 1/true/yes (default False)."""
    return os.environ.get("INJ_NEWS_ENABLED", "").strip().lower() in ("1", "true", "yes")
