"""Message-level helpers.

These wrappers keep the public surface close to the high-level client while
offering names that are convenient in scripts and examples.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from maxbridge.core.models import Message

if TYPE_CHECKING:
    from maxbridge.core.client import MaxBridgeClient


class MessageAPI:
    """Convenience wrapper for outgoing messages."""

    def __init__(self, client: "MaxBridgeClient") -> None:
        """Bind the wrapper to a high-level client instance."""

        self._client = client

    async def send(
        self, chat_id: str, text: str, *, reply_to_message_id: str | None = None
    ) -> Message:
        """Send one message through the high-level client."""

        return await self._client.send_text_message(
            chat_id, text, reply_to_message_id=reply_to_message_id
        )
