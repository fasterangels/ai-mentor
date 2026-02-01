"""Match resolver: deterministic logic to resolve user input into canonical matches.

This module provides a resolver that takes textual team names and optional
date hints and returns a canonical Match or explicit AMBIGUOUS/NOT_FOUND status.
No data fetching, no analyzer logic - uses repositories only.
"""

from .match_resolver import resolve_match
from .types import MatchResolutionInput, MatchResolutionOutput

__all__ = [
    "resolve_match",
    "MatchResolutionInput",
    "MatchResolutionOutput",
]
