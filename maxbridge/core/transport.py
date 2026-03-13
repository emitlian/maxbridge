"""Stable transport interfaces for MAXBRIDGE.

Concrete MAX adapter implementations live under ``maxbridge.experimental``.
The stable core depends only on this abstract contract.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator

from maxbridge.core.models import (
    Account,
    Chat,
    Message,
    Reaction,
    TypingStatus,
    UpdateEvent,
    User,
)


class AbstractMaxTransport(ABC):
    """Abstract transport for MAX operations.

    The stable core only relies on this contract. Real MAX behavior, mocks, or
    replay-backed adapters should all implement it.
    """

    @abstractmethod
    async def connect(self) -> None:
        """Open the transport."""

    @abstractmethod
    async def close(self) -> None:
        """Close the transport."""

    @abstractmethod
    async def get_account(self) -> Account | None:
        """Return the active account if available."""

    @abstractmethod
    async def get_user(self, user_id: str) -> User | None:
        """Return a user by ID."""

    @abstractmethod
    async def list_chats(self) -> list[Chat]:
        """List available chats."""

    @abstractmethod
    async def fetch_history(self, chat_id: str, *, limit: int = 100) -> list[Message]:
        """Fetch chat history."""

    @abstractmethod
    async def iter_updates(self, *, limit: int | None = None) -> AsyncIterator[UpdateEvent]:
        """Yield incoming updates."""

    @abstractmethod
    async def send_text_message(
        self, chat_id: str, text: str, *, reply_to_message_id: str | None = None
    ) -> Message:
        """Send a text message."""

    @abstractmethod
    async def send_reaction(self, chat_id: str, message_id: str, emoji: str) -> Reaction:
        """Send a reaction."""

    @abstractmethod
    async def set_typing(self, chat_id: str, *, enabled: bool) -> TypingStatus:
        """Set typing indicator state."""
