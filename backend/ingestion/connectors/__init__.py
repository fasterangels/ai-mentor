"""Data connector implementations."""

from .base import DataConnector
from .dummy import DummyConnector

__all__ = [
    "DataConnector",
    "DummyConnector",
]
