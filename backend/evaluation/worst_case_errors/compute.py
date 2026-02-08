"""
Aggregate evaluated decisions into a ranked worst-case report.
Inputs: evaluation records (EvaluatedDecision) + optional uncertainty_shadow already on each decision.
Output: WorstCaseReport (rows sorted by score desc, then fixture_id; computed_at_utc).
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import List

from .model import EvaluatedDecision, WorstCaseReport, WorstCaseRow
from .score import worst_case_score


def compute_worst_case_report(
    decisions: List[EvaluatedDecision],
    top_n: int | None = None,
    computed_at_utc: datetime | None = None,
) -> WorstCaseReport:
    """
    Build a ranked worst-case report from evaluated decisions.

    - Scores each decision; builds WorstCaseRow with triggered_uncertainty_signals/snapshot_ids when available.
    - Sorts by worst_case_score descending, then fixture_id ascending (stable tie-break).
    - If top_n is set, returns only the first top_n rows (overall). Otherwise returns all rows.
    """
    if computed_at_utc is None:
        computed_at_utc = datetime.now(timezone.utc)
    if computed_at_utc.tzinfo is None:
        computed_at_utc = computed_at_utc.replace(tzinfo=timezone.utc)

    rows: List[WorstCaseRow] = []
    for d in decisions:
        score = worst_case_score(d)
        signals = None
        if d.uncertainty_shadow is not None and d.uncertainty_shadow.triggered_uncertainty_signals:
            signals = list(d.uncertainty_shadow.triggered_uncertainty_signals)
        rows.append(
            WorstCaseRow(
                fixture_id=d.fixture_id,
                market=d.market,
                prediction=d.prediction,
                outcome=d.outcome,
                original_confidence=d.original_confidence,
                worst_case_score=score,
                triggered_uncertainty_signals=signals,
                snapshot_ids=list(d.snapshot_ids) if d.snapshot_ids else None,
                snapshot_type=d.snapshot_type,
            )
        )

    # Stable sort: score descending, then fixture_id ascending
    rows.sort(key=lambda r: (-r.worst_case_score, r.fixture_id))

    if top_n is not None and top_n >= 0:
        rows = rows[:top_n]

    return WorstCaseReport(rows=rows, computed_at_utc=computed_at_utc)
