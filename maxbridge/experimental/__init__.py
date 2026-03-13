"""Experimental MAX adapter layer.

This package is the explicit boundary for unstandardized MAX integrations,
including the mock transport used for local development and dry-run demos.
"""

from maxbridge.experimental.max_adapter import (
    MockMaxTransport,
    UnsupportedMaxTransport,
    build_max_transport,
)

__all__ = ["MockMaxTransport", "UnsupportedMaxTransport", "build_max_transport"]
