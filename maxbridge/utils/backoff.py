"""Retry and backoff utilities.

Backoff helpers are small now, but they document the intended direction for
future reconnect and retry policies in the stable runtime.
"""

from __future__ import annotations

from collections.abc import Iterator


def exponential_backoff(
    *, base: float = 0.5, factor: float = 2.0, maximum: float = 30.0
) -> Iterator[float]:
    """Yield exponential backoff intervals forever."""

    current = base
    while True:
        yield min(current, maximum)
        current *= factor
