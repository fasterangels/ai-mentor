"""
Injury-specific error taxonomy for evaluation (descriptive; no decision changes).
Scaffolding + counters; FALSE_OUT/FALSE_FIT require appearance ground truth (capability check).
"""

from __future__ import annotations

from typing import Any, Dict

# Taxonomy codes (evaluation reporting only)
INJ_FALSE_OUT = "INJ_FALSE_OUT"  # model marked OUT/QUESTIONABLE strongly, player appeared (needs appearance data)
INJ_FALSE_FIT = "INJ_FALSE_FIT"  # model marked AVAILABLE strongly, player did not appear (needs appearance data)
INJ_CONFLICT_UNRESOLVED = "INJ_CONFLICT_UNRESOLVED"
INJ_STALE_DATA_USED = "INJ_STALE_DATA_USED"  # resolution from claims older than policy max_age (needs claim timestamps)
INJ_COVERAGE_MISSING = "INJ_COVERAGE_MISSING"
INJ_PLAYER_MAPPING_FAIL = "INJ_PLAYER_MAPPING_FAIL"  # reserved; only if mapping exists

ALL_INJURY_TAXONOMY_CODES = frozenset({
    INJ_FALSE_OUT,
    INJ_FALSE_FIT,
    INJ_CONFLICT_UNRESOLVED,
    INJ_STALE_DATA_USED,
    INJ_COVERAGE_MISSING,
    INJ_PLAYER_MAPPING_FAIL,
})

# Cap for report size
MAX_REASONS_EMITTED_ENTRIES = 20


def compute_injury_evaluation_summary(injury_news_shadow_summary: Dict[str, Any]) -> Dict[str, Any]:
    """
    Compute injury_evaluation_summary from injury_news_shadow_summary (pipeline report section).
    Deterministic, bounded. No decision changes; evaluation/reporting only.
    """
    if not injury_news_shadow_summary or not injury_news_shadow_summary.get("enabled"):
        return {
            "coverage": {"fixtures_with_injury_shadow": 0, "teams_with_any_resolution": 0, "teams_with_no_resolution": 0},
            "conflicts": {"conflicts_count": 0, "conflicts_rate": 0.0},
            "staleness": {"stale_count": 0, "note": "needs claim timestamps linkage"},
            "reasons_emitted_counts": {},
        }

    resolutions_count = int(injury_news_shadow_summary.get("resolutions_count") or 0)
    reasons = injury_news_shadow_summary.get("reasons") or []

    team_refs_requested = int(injury_news_shadow_summary.get("team_refs_requested") or 0)
    teams_with_any_resolution = int(injury_news_shadow_summary.get("teams_with_any_resolution") or (2 if resolutions_count > 0 else 0))
    teams_with_no_resolution = max(0, team_refs_requested - teams_with_any_resolution) if team_refs_requested else (0 if resolutions_count > 0 else 2)

    fixtures_with_injury_shadow = 1 if resolutions_count > 0 else 0

    has_conflict = any(
        (r.get("code") or "").strip() in ("INJ_CONFLICT_PRESENT",)
        for r in reasons
    )
    conflicts_count = 1 if has_conflict else 0
    conflicts_rate = round(1.0 if has_conflict else 0.0, 4)

    reasons_emitted_counts: Dict[str, Any] = {}
    for r in reasons[:MAX_REASONS_EMITTED_ENTRIES]:
        code = (r.get("code") or "").strip()
        if not code:
            continue
        if code not in reasons_emitted_counts:
            reasons_emitted_counts[code] = {"overall": 0, "by_market": {"1X2": 0, "OU_2.5": 0, "BTTS": 0}}
        reasons_emitted_counts[code]["overall"] = reasons_emitted_counts[code]["overall"] + 1
        # Injury reasons are fixture-level; by_market left 0 until per-market attribution exists
    for code in reasons_emitted_counts:
        reasons_emitted_counts[code]["by_market"] = dict(sorted(reasons_emitted_counts[code]["by_market"].items()))

    return {
        "coverage": {
            "fixtures_with_injury_shadow": fixtures_with_injury_shadow,
            "teams_with_any_resolution": teams_with_any_resolution,
            "teams_with_no_resolution": teams_with_no_resolution,
        },
        "conflicts": {
            "conflicts_count": conflicts_count,
            "conflicts_rate": conflicts_rate,
        },
        "staleness": {
            "stale_count": 0,
            "note": "needs claim timestamps linkage",
        },
        "reasons_emitted_counts": dict(sorted(reasons_emitted_counts.items())),
    }
