"""
Unit tests for live awareness (J2 Part A).
- No live snapshots -> has_live_shadow=false
- Both present -> correct latest timestamps + gap
- Deterministic output ordering
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from live_awareness import compute_live_awareness, LiveAwarenessState
from live_awareness.reporting import state_to_dict, write_live_awareness_json


def _mock_row(payload_json: str, fetched_at_utc: datetime) -> MagicMock:
    row = MagicMock()
    row.payload_json = payload_json
    row.fetched_at_utc = fetched_at_utc
    return row


@pytest.mark.asyncio
async def test_no_live_snapshots_has_live_shadow_false() -> None:
    """When there are no live_shadow snapshots for the fixture, has_live_shadow is False."""
    fixture_id = "f1"
    now = datetime(2025, 6, 1, 12, 0, 0, tzinfo=timezone.utc)
    from pipeline.snapshot_envelope import build_envelope_for_recorded
    payload = {"match_id": fixture_id, "data": {}}
    env = build_envelope_for_recorded(payload, "rec_sid", now, "pipeline_cache")
    rec_json = json.dumps({"metadata": env.to_dict(), "payload": payload}, sort_keys=True, default=str)

    mock_repo = MagicMock()
    async def list_rows(source_name: str, match_id: str):
        if source_name == "live_shadow":
            return []
        if source_name == "pipeline_cache" and match_id == fixture_id:
            return [_mock_row(rec_json, now)]
        return []
    mock_repo.list_rows_by_source_and_match_id = AsyncMock(side_effect=list_rows)

    mock_session = MagicMock()
    def get_repo(_):
        return mock_repo
    with pytest.MonkeyPatch.context() as m:
        from live_awareness import compute as compute_mod
        m.setattr(compute_mod, "RawPayloadRepository", lambda session: mock_repo)
        state = await compute_live_awareness(mock_session, fixture_id)

    assert state.has_live_shadow is False
    assert state.scope_id == fixture_id
    assert state.latest_live_observed_at_utc is None
    assert state.latest_recorded_observed_at_utc is not None
    assert state.observed_gap_ms is None


@pytest.mark.asyncio
async def test_both_present_correct_timestamps_and_gap() -> None:
    """When both recorded and live_shadow exist, latest timestamps and observed_gap_ms are correct."""
    fixture_id = "f2"
    rec_ts = datetime(2025, 6, 1, 12, 0, 0, tzinfo=timezone.utc)
    live_ts = datetime(2025, 6, 1, 12, 5, 30, tzinfo=timezone.utc)  # 5m30s later
    from pipeline.snapshot_envelope import build_envelope_for_recorded, build_envelope_for_live_shadow
    payload_rec = {"match_id": fixture_id, "data": {}}
    payload_live = {"fixture_id": fixture_id, "data": {}}
    env_rec = build_envelope_for_recorded(payload_rec, "rec_sid", rec_ts, "pipeline_cache")
    env_live = build_envelope_for_live_shadow(payload_live, "live_sid", live_ts, "live_shadow", live_ts)
    rec_json = json.dumps({"metadata": env_rec.to_dict(), "payload": payload_rec}, sort_keys=True, default=str)
    live_json = json.dumps({"metadata": env_live.to_dict(), "payload": payload_live}, sort_keys=True, default=str)

    mock_repo = MagicMock()
    async def list_rows(source_name: str, match_id: str):
        if source_name == "pipeline_cache" and match_id == fixture_id:
            return [_mock_row(rec_json, rec_ts)]
        if source_name == "live_shadow" and match_id == fixture_id:
            return [_mock_row(live_json, live_ts)]
        return []
    mock_repo.list_rows_by_source_and_match_id = AsyncMock(side_effect=list_rows)

    mock_session = MagicMock()
    with pytest.MonkeyPatch.context() as m:
        from live_awareness import compute as compute_mod
        m.setattr(compute_mod, "RawPayloadRepository", lambda session: mock_repo)
        state = await compute_live_awareness(mock_session, fixture_id)

    assert state.has_live_shadow is True
    assert state.scope_id == fixture_id
    assert state.latest_recorded_observed_at_utc == rec_ts.isoformat()
    assert state.latest_live_observed_at_utc == live_ts.isoformat()
    # gap = live - recorded = 5*60 + 30 = 330 seconds = 330_000 ms
    assert state.observed_gap_ms == 330_000


def test_deterministic_output_ordering() -> None:
    """state_to_dict and written JSON have stable key ordering."""
    from datetime import datetime, timezone
    now = datetime(2025, 6, 1, 12, 0, 0, tzinfo=timezone.utc)
    state = LiveAwarenessState(
        schema_version=1,
        computed_at_utc=now,
        scope_id="f1",
        has_live_shadow=True,
        latest_live_observed_at_utc="2025-06-01T12:00:00+00:00",
        latest_recorded_observed_at_utc="2025-06-01T11:00:00+00:00",
        observed_gap_ms=3600000,
        notes=None,
    )
    d = state_to_dict(state)
    keys = list(d.keys())
    expected_order = [
        "schema_version",
        "computed_at_utc",
        "scope_id",
        "has_live_shadow",
        "latest_live_observed_at_utc",
        "latest_recorded_observed_at_utc",
        "observed_gap_ms",
        "notes",
    ]
    assert keys == expected_order

    import tempfile
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        path = f.name
    try:
        write_live_awareness_json(state, path)
        raw = Path(path).read_text(encoding="utf-8")
        parsed = json.loads(raw)
        assert list(parsed.keys()) == expected_order
    finally:
        Path(path).unlink(missing_ok=True)
