"""
Pure deterministic injury shadow feature computation from resolution records.
Input: list of resolution records (dict or object with team_ref, player_ref, resolved_status,
       resolution_confidence, resolution_method, resolution_id).
Output: bounded dict with counts, uncertainty_index, key_items. No live IO.
"""

from __future__ import annotations

from typing import Any, Dict, List, Union

# Weights for uncertainty_index: weight * (1 - confidence) per resolution, then sum, rounded to 4 decimals.
# OUT and SUSPENDED = 1.0, QUESTIONABLE = 0.5, UNKNOWN = 0.25, AVAILABLE = 0.
STATUS_WEIGHT: Dict[str, float] = {
    "OUT": 1.0,
    "SUSPENDED": 1.0,
    "QUESTIONABLE": 0.5,
    "UNKNOWN": 0.25,
    "AVAILABLE": 0.0,
}
DEFAULT_WEIGHT = 0.25  # status not in STATUS_WEIGHT -> treat as UNKNOWN


def _get(r: Union[Dict[str, Any], Any], key: str, default: Any = None) -> Any:
    """Get attribute from dict or object."""
    if isinstance(r, dict):
        return r.get(key, default)
    return getattr(r, key, default)


def _weight(status: str) -> float:
    """Weight for resolved_status (deterministic)."""
    return STATUS_WEIGHT.get((status or "").strip().upper(), DEFAULT_WEIGHT)


def compute_injury_shadow_features(
    resolutions: List[Union[Dict[str, Any], Any]],
    *,
    top_k: int = 5,
) -> Dict[str, Any]:
    """
    Compute injury shadow features from a list of resolution records.

    Input records must have: team_ref, player_ref (nullable), resolved_status,
    resolution_confidence, resolution_method, resolution_id.

    Output (deterministic, bounded):
      - out_count, questionable_count, suspended_count, unknown_count
      - uncertainty_index: round(sum(weight(status) * (1 - confidence)), 4)
      - key_items: up to top_k items, sorted by weight desc, then resolution_confidence
        asc (lower confidence first to highlight risk), then player_ref, then resolution_id.
        Each item: player_ref, resolved_status, resolution_confidence, resolution_id.
    """
    out_count = 0
    questionable_count = 0
    suspended_count = 0
    unknown_count = 0
    uncertainty_sum = 0.0

    for r in resolutions:
        status = (_get(r, "resolved_status") or "").strip().upper()
        conf = float(_get(r, "resolution_confidence", 0.0))
        conf = max(0.0, min(1.0, conf))
        w = _weight(status)
        uncertainty_sum += w * (1.0 - conf)
        if status == "OUT":
            out_count += 1
        elif status == "QUESTIONABLE":
            questionable_count += 1
        elif status == "SUSPENDED":
            suspended_count += 1
        elif status == "UNKNOWN" or status == "":
            unknown_count += 1
        # AVAILABLE not counted in out/questionable/suspended/unknown

    uncertainty_index = round(uncertainty_sum, 4)

    # key_items: sort by (-weight, confidence asc, player_ref, resolution_id) for stable order
    def _key_item(r: Union[Dict[str, Any], Any]) -> tuple:
        status = (_get(r, "resolved_status") or "").strip().upper()
        w = _weight(status)
        conf = float(_get(r, "resolution_confidence", 0.0))
        player = _get(r, "player_ref")
        player_ref = "" if player is None else str(player)
        res_id = _get(r, "resolution_id")
        res_id_str = "" if res_id is None else str(res_id)
        # weight desc, then confidence asc (lower first), then player_ref, then resolution_id
        return (-w, conf, player_ref, res_id_str)

    sorted_res = sorted(resolutions, key=_key_item)
    key_items = []
    for r in sorted_res[:top_k]:
        key_items.append({
            "player_ref": "" if _get(r, "player_ref") is None else str(_get(r, "player_ref")),
            "resolved_status": (_get(r, "resolved_status") or "").strip() or "UNKNOWN",
            "resolution_confidence": round(float(_get(r, "resolution_confidence", 0.0)), 4),
            "resolution_id": "" if _get(r, "resolution_id") is None else str(_get(r, "resolution_id")),
        })

    return {
        "out_count": out_count,
        "questionable_count": questionable_count,
        "suspended_count": suspended_count,
        "unknown_count": unknown_count,
        "uncertainty_index": uncertainty_index,
        "key_items": key_items,
    }
