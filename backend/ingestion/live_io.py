"""
Safe live IO wrapper: recorded-first enforcement, read-only default.
Connectors are only exposed when they are RecordedPlatformAdapter or when live IO is explicitly allowed.
"""

from __future__ import annotations

import os
from typing import Optional

from ingestion.connectors.platform_base import DataConnector, RecordedPlatformAdapter
from ingestion.registry import get_connector


def live_io_allowed() -> bool:
    """True if live (non-recorded) connectors are allowed. Default: False (recorded-first)."""
    return os.environ.get("LIVE_IO_ALLOWED", "").strip().lower() in ("1", "true", "yes")


def live_writes_allowed() -> bool:
    """True if live writes (e.g. persist, cache) are allowed. Default: False (read-only default)."""
    return os.environ.get("LIVE_WRITES_ALLOWED", "").strip().lower() in ("1", "true", "yes")


def get_connector_safe(name: str) -> Optional[DataConnector]:
    """
    Return the connector only if it is safe to use under current policy:
    - RecordedPlatformAdapter: always allowed (recorded-first).
    - Other connectors: only when LIVE_IO_ALLOWED is true.
    Returns None if not found or not allowed.
    """
    adapter = get_connector(name)
    if adapter is None:
        return None
    if isinstance(adapter, RecordedPlatformAdapter):
        return adapter
    if live_io_allowed():
        return adapter
    return None
