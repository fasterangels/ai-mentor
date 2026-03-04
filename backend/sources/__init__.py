from __future__ import annotations

"""
Online data source plugin architecture (MVP).

This package defines the source interfaces and built-in implementations:
- base protocol and dataclasses (`base`)
- mock source (`mock_source`)
- generic HTTP JSON source (`http_json_source`)
- simple in-process registry (`registry`)
"""

from .base import FetchRequest, FetchResult, DataSource

__all__ = ["FetchRequest", "FetchResult", "DataSource"]

