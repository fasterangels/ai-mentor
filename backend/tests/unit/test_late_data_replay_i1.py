"""
Unit tests for I1 Part A: late-data replay scenario generator.
- Delayed observed_at applies correct offsets
- payload_checksum unchanged, envelope_checksum changes
- Deterministic scenario ids / filenames
- Missing timing fields variant drops only allowed fields and remains readable
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Force backend at sys.path[0] so it is found before the test dir pytest adds (repo root or CI)
_backend = Path(__file__).resolve().parent.parent.parent
if not (_backend / "pipeline").exists():
    for _cand in [Path.cwd() / "backend", Path.cwd(), Path.cwd().parent / "backend"]:
        if (_cand / "pipeline").exists():
            _backend = _cand
            break
_add = str(_backend)
if _add not in sys.path:
    sys.path.insert(0, _add)

from pipeline.snapshot_envelope import compute_payload_checksum, compute_envelope_checksum
from replay.late_data.generate import (
    DELAY_OFFSET_MINUTES,
    apply_delayed_observed_at,
    apply_missing_timing_tags,
    apply_stale_effective_from,
    derived_payload_json,
    generate_variant_metadata,
    generate_delayed_observed_at_scenarios,
    generate_missing_timing_tags_scenario,
    generate_stale_effective_from_scenarios,
)
from replay.late_data.model import ScenarioType
from replay.late_data.storage import scenario_filename, LATE_DATA_SCENARIOS_DIR


def _minimal_meta(observed_at_utc: str = "2025-01-15T12:00:00+00:00") -> dict:
    payload = {"match_id": "m1", "x": 1}
    return {
        "snapshot_id": "sid_base",
        "snapshot_type": "recorded",
        "created_at_utc": "2025-01-15T11:00:00+00:00",
        "payload_checksum": compute_payload_checksum(payload),
        "source": {"class": "RECORDED", "name": "recorded", "ref": None, "reliability_tier": "HIGH"},
        "observed_at_utc": observed_at_utc,
        "schema_version": 1,
    }


def test_delayed_observed_at_applies_correct_offsets() -> None:
    meta = _minimal_meta("2025-01-15T12:00:00+00:00")
    payload = {"match_id": "m1", "x": 1}

    # +15m
    derived = apply_delayed_observed_at(meta, 15)
    assert derived["observed_at_utc"] == "2025-01-15T12:15:00+00:00"
    # +1h
    derived1h = apply_delayed_observed_at(meta, 60)
    assert derived1h["observed_at_utc"] == "2025-01-15T13:00:00+00:00"
    # +24h
    derived24h = apply_delayed_observed_at(meta, 24 * 60)
    assert derived24h["observed_at_utc"] == "2025-01-16T12:00:00+00:00"

    # Fixed offsets list used in generator
    for delay_min in DELAY_OFFSET_MINUTES:
        scenario, d = generate_variant_metadata(
            meta, payload, ScenarioType.DELAYED_OBSERVED_AT, {"delay_minutes": delay_min}, "m1", "2025-01-15T14:00:00+00:00"
        )
        assert d["scenario"]["parameters"]["delay_minutes"] == delay_min
        # observed_at should be base + delay
        base_obs = "2025-01-15T12:00:00+00:00"
        if delay_min == 15:
            assert d["observed_at_utc"] == "2025-01-15T12:15:00+00:00"
        elif delay_min == 60:
            assert d["observed_at_utc"] == "2025-01-15T13:00:00+00:00"


def test_payload_checksum_unchanged_envelope_checksum_changes() -> None:
    meta = _minimal_meta()
    meta["envelope_checksum"] = compute_envelope_checksum(meta)
    payload = {"match_id": "m1", "x": 1}
    original_payload_cs = meta["payload_checksum"]
    original_env_cs = meta["envelope_checksum"]

    scenario, derived = generate_variant_metadata(
        meta, payload, ScenarioType.DELAYED_OBSERVED_AT, {"delay_minutes": 15}, "m1", "2025-01-15T14:00:00+00:00"
    )

    assert derived["payload_checksum"] == original_payload_cs
    assert derived["payload_checksum"] == compute_payload_checksum(payload)
    assert derived["envelope_checksum"] != original_env_cs
    assert "scenario" in derived
    # Changing timing + adding scenario changes envelope checksum
    assert compute_envelope_checksum(derived) == derived["envelope_checksum"]


def test_deterministic_scenario_ids_and_filenames() -> None:
    meta = _minimal_meta()
    payload = {"match_id": "m1", "x": 1}
    fixture_id = "m1"
    created = "2025-01-15T14:00:00+00:00"

    s1, _ = generate_variant_metadata(meta, payload, ScenarioType.DELAYED_OBSERVED_AT, {"delay_minutes": 15}, fixture_id, created)
    s2, _ = generate_variant_metadata(meta, payload, ScenarioType.DELAYED_OBSERVED_AT, {"delay_minutes": 15}, fixture_id, created)

    assert s1.scenario_id == s2.scenario_id
    assert scenario_filename(s1.scenario_id) == scenario_filename(s2.scenario_id)

    # Different params -> different id
    s3, _ = generate_variant_metadata(meta, payload, ScenarioType.DELAYED_OBSERVED_AT, {"delay_minutes": 60}, fixture_id, created)
    assert s3.scenario_id != s1.scenario_id

    # Delayed scenarios: deterministic order and ids
    list_delayed = generate_delayed_observed_at_scenarios(meta, payload, fixture_id, created)
    ids = [sc.scenario_id for sc, _ in list_delayed]
    assert len(ids) == len(set(ids))
    assert len(ids) == len(DELAY_OFFSET_MINUTES)


def test_missing_timing_variant_drops_only_allowed_fields_and_remains_readable() -> None:
    meta = _minimal_meta()
    meta["fetch_started_at_utc"] = "2025-01-15T11:59:00+00:00"
    meta["fetch_ended_at_utc"] = "2025-01-15T12:00:00+00:00"
    meta["latency_ms"] = 100.5
    meta["effective_from_utc"] = "2025-01-15T10:00:00+00:00"
    meta["expected_valid_until_utc"] = "2025-01-16T00:00:00+00:00"
    payload = {"match_id": "m1", "x": 1}

    scenario, derived = generate_missing_timing_tags_scenario(meta, payload, "m1", "2025-01-15T14:00:00+00:00")

    assert "fetch_started_at_utc" not in derived
    assert "fetch_ended_at_utc" not in derived
    assert "latency_ms" not in derived
    assert "effective_from_utc" not in derived
    assert "expected_valid_until_utc" not in derived

    assert derived["observed_at_utc"] == meta["observed_at_utc"]
    assert derived["snapshot_id"] == meta["snapshot_id"]
    assert derived["payload_checksum"] == meta["payload_checksum"]
    assert derived["schema_version"] == meta["schema_version"]
    assert "scenario" in derived

    # Remain readable as envelope
    payload_json = derived_payload_json(derived, payload)
    parsed = json.loads(payload_json)
    assert "metadata" in parsed and "payload" in parsed
    assert parsed["metadata"]["snapshot_id"] == "sid_base"
    assert parsed["payload"] == payload


def test_stale_effective_from_offsets() -> None:
    meta = _minimal_meta()
    meta["effective_from_utc"] = "2025-01-15T10:00:00+00:00"
    payload = {"match_id": "m1", "x": 1}

    derived_earlier = apply_stale_effective_from(meta, -60)
    assert derived_earlier["effective_from_utc"] == "2025-01-15T09:00:00+00:00"

    derived_later = apply_stale_effective_from(meta, 60)
    assert derived_later["effective_from_utc"] == "2025-01-15T11:00:00+00:00"

    # When effective_from missing, uses observed_at
    meta_no_eff = _minimal_meta("2025-01-15T12:00:00+00:00")
    meta_no_eff.pop("effective_from_utc", None)
    derived_from_obs = apply_stale_effective_from(meta_no_eff, 120)
    assert derived_from_obs["effective_from_utc"] == "2025-01-15T14:00:00+00:00"


def test_storage_dir_constant() -> None:
    assert "replay_scenarios" in LATE_DATA_SCENARIOS_DIR
    assert "late_data" in LATE_DATA_SCENARIOS_DIR
    assert scenario_filename("abc12") == "abc12.json"
