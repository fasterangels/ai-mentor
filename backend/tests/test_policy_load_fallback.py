"""Policy load: missing or invalid file => default_policy used (no crash)."""

from __future__ import annotations

import os
import sys
from pathlib import Path

_backend = Path(__file__).resolve().parent.parent
if str(_backend) not in sys.path:
    sys.path.insert(0, str(_backend))


def test_missing_policy_uses_default():
    """When POLICY_PATH points to missing file, get_active_policy returns default."""
    from policy.policy_runtime import get_active_policy
    from policy.policy_store import default_policy

    orig = os.environ.pop("POLICY_PATH", None)
    try:
        os.environ["POLICY_PATH"] = str(Path("/nonexistent/policy_xyz_absent.json"))
        policy = get_active_policy()
        default = default_policy()
        assert policy.meta.version == default.meta.version
        assert list(policy.markets.keys()) == list(default.markets.keys())
        for k in default.markets:
            assert policy.markets[k].min_confidence == default.markets[k].min_confidence
    finally:
        if orig is not None:
            os.environ["POLICY_PATH"] = orig
        else:
            os.environ.pop("POLICY_PATH", None)


def test_invalid_policy_file_uses_default():
    """When policy file exists but is invalid JSON/corrupt, get_active_policy returns default."""
    import tempfile
    from policy.policy_runtime import get_active_policy
    from policy.policy_store import default_policy

    orig = os.environ.get("POLICY_PATH")
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        f.write("not valid json {")
        bad_path = f.name
    try:
        os.environ["POLICY_PATH"] = bad_path
        policy = get_active_policy()
        default = default_policy()
        assert policy.meta.version == default.meta.version
    finally:
        Path(bad_path).unlink(missing_ok=True)
        if orig is not None:
            os.environ["POLICY_PATH"] = orig
        else:
            os.environ.pop("POLICY_PATH", None)


def test_default_policy_has_expected_structure():
    """default_policy() returns Policy with all required markets and sane min_confidence."""
    from policy.policy_store import default_policy

    p = default_policy()
    assert p.meta.version == "v0"
    assert "one_x_two" in p.markets
    assert "over_under_25" in p.markets
    assert "gg_ng" in p.markets
    for m in p.markets.values():
        assert 0.0 <= m.min_confidence <= 1.0
        assert m.min_confidence == 0.62
