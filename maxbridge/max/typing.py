"""Typing helpers."""

from __future__ import annotations

from typing import TYPE_CHECKING

from maxbridge.core.models import TypingStatus

if TYPE_CHECKING:
    from maxbridge.core.client import MaxBridgeClient


class TypingAPI:
    """Convenience wrapper for typing indicators."""

    def __init__(self, client: "MaxBridgeClient") -> None:
        """Bind the wrapper to a high-level client instance."""

        self._client = client

    async def set(self, chat_id: str, *, enabled: bool) -> TypingStatus:
        """Toggle a typing indicator through the high-level client."""

        return await self._client.set_typing(chat_id, enabled=enabled)
