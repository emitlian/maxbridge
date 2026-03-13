"""MAXBRIDGE public package interface."""

from maxbridge.config import MaxBridgeConfig, load_config
from maxbridge.core.client import MaxBridgeClient

__all__ = ["MaxBridgeClient", "MaxBridgeConfig", "load_config"]

__version__ = "0.1.0a0"
