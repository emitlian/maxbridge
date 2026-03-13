"""Dialog-level helpers.

These wrappers provide a small ergonomic layer over the stable high-level
client without introducing a second abstraction model.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from maxbridge.core.models import Chat, Message

if TYPE_CHECKING:
    from maxbridge.core.client import MaxBridgeClient


class DialogAPI:
    """Convenience wrapper for dialogs and history."""

    def __init__(self, client: "MaxBridgeClient") -> None:
        """Bind the wrapper to a high-level client instance."""

        self._client = client

    async def list(self) -> list[Chat]:
        """Return chats visible to the current runtime."""

        return await self._client.get_chats()

    async def history(self, chat_id: str, *, limit: int = 100) -> list[Message]:
        """Return message history for one chat."""

        return await self._client.get_history(chat_id, limit=limit)
