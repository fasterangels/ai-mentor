"""
Baseline immutability helpers.

Defines a BaselineRun concept and a deterministic hash over:
- analyzer version (string)
- policy JSON content (canonicalized)
- schema versions (explicit mapping)

Hash input shape (keys sorted in JSON before hashing):

    {
        "analyzer_version": "<str>",
        "policy_digest": "<hex sha256 of policy JSON>",
        "schema_versions": {
            "<name>": "<version or numeric>"
        }
    }

The final baseline_hash is SHA256 over the UTF-8 JSON representation of
that object with sort_keys=True and compact separators.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Dict

from policy.policy_store import stable_json_dumps


@dataclass(frozen=True)
class BaselineRun:
    """
    Frozen baseline evaluation run descriptor.

    Read-only instrumentation: does not affect analyzer decisions,
    confidences, refusals, or reasons. Intended to be embedded in
    evaluation report metadata.
    """

    analyzer_version: str
    policy_digest: str
    schema_versions: Dict[str, Any]
    baseline_hash: str


def _baseline_input(
    analyzer_version: str,
    policy_digest: str,
    schema_versions: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Canonical baseline input object.

    This exact shape (with keys sorted when serialized) is what feeds into
    the baseline_hash computation. Do not change lightly.
    """
    return {
        "analyzer_version": analyzer_version,
        "policy_digest": policy_digest,
        "schema_versions": schema_versions,
    }


def build_baseline_run(
    analyzer_version: str,
    policy_payload: Dict[str, Any],
    schema_versions: Dict[str, Any],
) -> BaselineRun:
    """
    Compute BaselineRun from explicit components.

    - policy_digest: SHA256 over canonical JSON of policy_payload
      (stable_json_dumps, sort_keys=True, no extra whitespace)
    - baseline_hash: SHA256 over canonical JSON of the baseline input object
      (analyzer_version + policy_digest + schema_versions), with keys sorted.
    """
    # Digest over full policy JSON content
    policy_json = stable_json_dumps(policy_payload)
    policy_digest = hashlib.sha256(policy_json.encode("utf-8")).hexdigest()

    # Baseline input includes analyzer version, policy digest, and schema versions
    baseline_obj = _baseline_input(analyzer_version, policy_digest, schema_versions)
    baseline_json = json.dumps(
        baseline_obj,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    baseline_hash = hashlib.sha256(baseline_json.encode("utf-8")).hexdigest()

    return BaselineRun(
        analyzer_version=analyzer_version,
        policy_digest=policy_digest,
        schema_versions=dict(schema_versions),
        baseline_hash=baseline_hash,
    )


def default_schema_versions() -> Dict[str, Any]:
    """
    Return schema versions that are relevant for baseline evaluation.

    This is intentionally a small, explicit mapping to avoid hidden
    dependencies. If additional schemas become baseline-critical, add
    them here.
    """
    from pipeline.snapshot_envelope import ENVELOPE_SCHEMA_VERSION
    from modeling.reason_decay.model import SCHEMA_VERSION as REASON_DECAY_SCHEMA_VERSION

    return {
        "snapshot_envelope": ENVELOPE_SCHEMA_VERSION,
        "reason_decay": REASON_DECAY_SCHEMA_VERSION,
    }

