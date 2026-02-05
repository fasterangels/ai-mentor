"""Registry of platform adapters by name."""

from __future__ import annotations

from typing import Any, Dict, Optional

from ingestion.connectors.platform_base import DataConnector
from ingestion.connectors.real_provider_2 import RealProvider2Adapter
from ingestion.connectors.sample_platform import SamplePlatformAdapter
from ingestion.connectors.sample_recorded_platform_v2 import SampleRecordedPlatformV2Adapter
from ingestion.connectors.stub_platform import StubPlatformAdapter
from ingestion.connectors.stub_live_platform import StubLivePlatformAdapter
from ingestion.connectors.real_provider import RealProviderAdapter

_REGISTRY: Dict[str, DataConnector] = {
    "sample_platform": SamplePlatformAdapter(),
    "sample_recorded_platform_v2": SampleRecordedPlatformV2Adapter(),
    "stub_platform": StubPlatformAdapter(),
    "stub_live_platform": StubLivePlatformAdapter(),
    "real_provider": RealProviderAdapter(),
    "real_provider_2": RealProvider2Adapter(),
}


def get_connector(name: str) -> Optional[DataConnector]:
    """Return the adapter registered under name, or None."""
    return _REGISTRY.get(name)


def list_registered_connectors() -> list[str]:
    """Return sorted list of registered connector names (for CI and tooling)."""
    return sorted(_REGISTRY.keys())


def register_connector(name: str, adapter: DataConnector) -> None:
    """Register an adapter under name (for tests or extensions)."""
    _REGISTRY[name] = adapter
