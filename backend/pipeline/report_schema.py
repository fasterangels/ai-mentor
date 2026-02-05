"""
Report schema versioning and validation for pipeline outputs.
Supported flows only; validator runs in pipeline/shadow path.
"""
from __future__ import annotations

import os
from typing import Any, Dict, List, Tuple

REPORT_SCHEMA_VERSION = "report.v1"
CANONICAL_FLOW_SHADOW_RUN = "/pipeline/shadow/run"
ALLOWED_SCHEMA_VERSIONS = (REPORT_SCHEMA_VERSION,)
REQUIRED_TOP_LEVEL_KEYS = (
    "schema_version",
    "canonical_flow",
    "ingestion",
    "analysis",
    "resolution",
    "evaluation_report_checksum",
    "proposal",
    "audit",
)


def get_validate_strict() -> bool:
    """Return True if REPORT_SCHEMA_VALIDATE_STRICT env is set to true/1/yes. Default False."""
    return os.environ.get("REPORT_SCHEMA_VALIDATE_STRICT", "false").strip().lower() in ("1", "true", "yes")


def validate_report_schema(report: Dict[str, Any], strict: bool = False) -> Tuple[bool, List[str]]:
    """
    Validate report payload shape. Required keys must exist; schema_version must be in allowed set.
    Returns (passed, list of error messages).
    """
    errors: List[str] = []
    if not isinstance(report, dict):
        errors.append("report must be a dict")
        return False, errors
    for key in REQUIRED_TOP_LEVEL_KEYS:
        if key not in report:
            errors.append(f"missing required key: {key!r}")
    schema_version = report.get("schema_version")
    if schema_version is not None and schema_version not in ALLOWED_SCHEMA_VERSIONS:
        errors.append(f"schema_version {schema_version!r} not in allowed set: {list(ALLOWED_SCHEMA_VERSIONS)}")
    elif schema_version is None:
        errors.append("missing required key: 'schema_version'")
    canonical_flow = report.get("canonical_flow")
    if canonical_flow is not None and canonical_flow != CANONICAL_FLOW_SHADOW_RUN:
        errors.append(f"canonical_flow must be {CANONICAL_FLOW_SHADOW_RUN!r}, got {canonical_flow!r}")
    passed = len(errors) == 0
    return passed, errors
