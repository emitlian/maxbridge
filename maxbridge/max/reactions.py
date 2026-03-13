"""Reaction helpers."""

from __future__ import annotations

from typing import TYPE_CHECKING

from maxbridge.core.models import Reaction

if TYPE_CHECKING:
    from maxbridge.core.client import MaxBridgeClient


class ReactionAPI:
    """Convenience wrapper for reactions."""

    def __init__(self, client: "MaxBridgeClient") -> None:
        """Bind the wrapper to a high-level client instance."""

        self._client = client

    async def react(self, chat_id: str, message_id: str, emoji: str) -> Reaction:
        """Send one reaction through the high-level client."""

        return await self._client.send_reaction(chat_id, message_id, emoji)
