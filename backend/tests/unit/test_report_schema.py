"""Unit tests for report schema validation."""
from __future__ import annotations
import sys
from pathlib import Path
_backend = Path(__file__).resolve().parent.parent.parent
if str(_backend) not in sys.path:
    sys.path.insert(0, str(_backend))
from pipeline.report_schema import (
    ALLOWED_SCHEMA_VERSIONS,
    CANONICAL_FLOW_SHADOW_RUN,
    REPORT_SCHEMA_VERSION,
    get_validate_strict,
    validate_report_schema,
)

def _valid_report():
    return {
        "schema_version": REPORT_SCHEMA_VERSION,
        "canonical_flow": CANONICAL_FLOW_SHADOW_RUN,
        "ingestion": {},
        "analysis": {},
        "resolution": {},
        "evaluation_report_checksum": None,
        "proposal": {},
        "audit": {},
    }

def test_validator_accepts_current_report_payload():
    passed, errs = validate_report_schema(_valid_report())
    assert passed is True
    assert errs == []

def test_validator_rejects_missing_schema_version():
    r = _valid_report()
    del r["schema_version"]
    passed, errs = validate_report_schema(r)
    assert passed is False
    assert any("schema_version" in e for e in errs)

def test_validator_rejects_invalid_schema_version():
    r = _valid_report()
    r["schema_version"] = "report.v99"
    passed, errs = validate_report_schema(r)
    assert passed is False
    assert any("not in allowed" in e for e in errs)
