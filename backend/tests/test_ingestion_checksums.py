"""Deterministic checksums: same object => same checksum; change => checksum changes."""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

_backend = Path(__file__).resolve().parent.parent
if str(_backend) not in sys.path:
    sys.path.insert(0, str(_backend))

from ingestion.checksums import ingested_checksum, odds_checksum, stable_json_dumps, sha256_hex
from ingestion.schema import IngestedMatchData, MatchIdentity, MatchState, OddsSnapshot


def test_stable_json_dumps_sorted_keys():
    """Same dict with different key order produces same output."""
    a = stable_json_dumps({"b": 1, "a": 2})
    b = stable_json_dumps({"a": 2, "b": 1})
    assert a == b


def test_sha256_hex_deterministic():
    """Same input => same hash."""
    assert sha256_hex("hello") == sha256_hex("hello")
    assert sha256_hex("hello") != sha256_hex("world")


def test_odds_checksum_same_object_same_checksum():
    """Same OddsSnapshot => same checksum."""
    dt = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    o1 = OddsSnapshot(market="1X2", selection="HOME", odds=2.0, source="x", collected_at_utc=dt)
    o2 = OddsSnapshot(market="1X2", selection="HOME", odds=2.0, source="x", collected_at_utc=dt)
    assert odds_checksum(o1) == odds_checksum(o2)


def test_odds_checksum_change_odds_changes_checksum():
    """Changing odds value changes checksum."""
    dt = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    o1 = OddsSnapshot(market="1X2", selection="HOME", odds=2.0, source="x", collected_at_utc=dt)
    o2 = OddsSnapshot(market="1X2", selection="HOME", odds=2.1, source="x", collected_at_utc=dt)
    assert odds_checksum(o1) != odds_checksum(o2)


def test_ingested_checksum_same_data_same_checksum():
    """Same IngestedMatchData => same checksum."""
    identity = MatchIdentity(
        match_id="m1", home_team="H", away_team="A", competition="C",
        kickoff_utc=datetime(2025, 1, 1, 15, 0, 0, tzinfo=timezone.utc),
    )
    dt = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    odds = [OddsSnapshot(market="1X2", selection="HOME", odds=2.0, source="x", collected_at_utc=dt)]
    state = MatchState(minute=None, score_home=None, score_away=None, status="SCHEDULED")
    data1 = IngestedMatchData(identity=identity, odds=odds, state=state)
    data2 = IngestedMatchData(identity=identity, odds=odds, state=state)
    assert ingested_checksum(data1) == ingested_checksum(data2)


def test_ingested_checksum_different_odds_different_checksum():
    """Different odds => different payload checksum."""
    identity = MatchIdentity(
        match_id="m1", home_team="H", away_team="A", competition="C",
        kickoff_utc=datetime(2025, 1, 1, 15, 0, 0, tzinfo=timezone.utc),
    )
    dt = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    odds1 = [OddsSnapshot(market="1X2", selection="HOME", odds=2.0, source="x", collected_at_utc=dt)]
    odds2 = [OddsSnapshot(market="1X2", selection="HOME", odds=2.1, source="x", collected_at_utc=dt)]
    state = MatchState(minute=None, score_home=None, score_away=None, status="SCHEDULED")
    data1 = IngestedMatchData(identity=identity, odds=odds1, state=state)
    data2 = IngestedMatchData(identity=identity, odds=odds2, state=state)
    assert ingested_checksum(data1) != ingested_checksum(data2)
