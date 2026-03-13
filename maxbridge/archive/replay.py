"""Replay event fixtures from JSON archives.

Replay support is part of the stable local-first toolchain. It lets the bridge
and archive layers evolve even when real MAX update streams are unavailable.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from pathlib import Path

from maxbridge.core.models import UpdateEvent


class ReplayEventSource:
    """Load update events from a JSON fixture for replay-based development."""

    def __init__(self, path: str | Path) -> None:
        """Store the replay fixture path."""

        self.path = Path(path)

    async def iter_events(self) -> AsyncIterator[UpdateEvent]:
        """Yield update events from the replay fixture in file order."""

        raw = json.loads(self.path.read_text(encoding="utf-8"))
        for item in raw:
            yield UpdateEvent.model_validate(item)
