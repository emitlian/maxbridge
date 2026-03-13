"""Experimental MAX adapter implementations.

These adapters are intentionally isolated from the stable core because real MAX
user-layer integration may depend on non-public or evolving interfaces.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator

from maxbridge.config.models import MaxBridgeConfig
from maxbridge.core.exceptions import TransportUnavailableError
from maxbridge.core.models import (
    Account,
    Chat,
    ChatType,
    EventType,
    Message,
    Reaction,
    TypingStatus,
    UpdateEvent,
    User,
)
from maxbridge.core.transport import AbstractMaxTransport
from maxbridge.utils.ids import stable_id
from maxbridge.utils.time import utc_now


class UnsupportedMaxTransport(AbstractMaxTransport):
    """Placeholder transport for unavailable MAX integrations.

    This class makes the experimental boundary explicit at runtime. It is
    better to fail clearly than to imply unsupported MAX behavior exists.
    """

    async def connect(self) -> None:
        """Fail fast when no experimental adapter is configured."""

        raise TransportUnavailableError(
            "No safe MAX transport adapter is configured. Use the experimental mock adapter."
        )

    async def close(self) -> None:
        return None

    async def get_account(self) -> Account | None:
        return None

    async def get_user(self, user_id: str) -> User | None:
        return None

    async def list_chats(self) -> list[Chat]:
        raise TransportUnavailableError("Chat listing is unavailable without a MAX adapter.")

    async def fetch_history(self, chat_id: str, *, limit: int = 100) -> list[Message]:
        raise TransportUnavailableError("History is unavailable without a MAX adapter.")

    async def iter_updates(self, *, limit: int | None = None) -> AsyncIterator[UpdateEvent]:
        if False:
            yield UpdateEvent(id="never", type=EventType.MESSAGE_NEW, chat_id="never")
        raise TransportUnavailableError("Updates are unavailable without a MAX adapter.")

    async def send_text_message(
        self, chat_id: str, text: str, *, reply_to_message_id: str | None = None
    ) -> Message:
        raise TransportUnavailableError("Sending is unavailable without a MAX adapter.")

    async def send_reaction(self, chat_id: str, message_id: str, emoji: str) -> Reaction:
        raise TransportUnavailableError("Reactions are unavailable without a MAX adapter.")

    async def set_typing(self, chat_id: str, *, enabled: bool) -> TypingStatus:
        raise TransportUnavailableError("Typing is unavailable without a MAX adapter.")


class MockMaxTransport(AbstractMaxTransport):
    """Deterministic in-memory transport for local development and tests.

    The mock transport is intentionally part of the experimental MAX layer. It
    demonstrates the stable bridge/runtime slice without pretending to be a
    real MAX integration.
    """

    def __init__(
        self,
        *,
        account: Account,
        users: list[User],
        chats: list[Chat],
        messages: dict[str, list[Message]],
    ) -> None:
        """Initialize the transport with fully in-memory seed data."""

        self._account = account
        self._users = {user.id: user for user in users}
        self._users.setdefault(
            account.id,
            User(id=account.id, username=account.username, display_name=account.display_name),
        )
        self._chats = {chat.id: chat for chat in chats}
        self._messages = {chat_id: list(items) for chat_id, items in messages.items()}
        self._updates: asyncio.Queue[UpdateEvent] = asyncio.Queue()
        for items in self._messages.values():
            for message in items:
                # Seed updates make replay-style demos deterministic.
                self._updates.put_nowait(
                    UpdateEvent(
                        id=stable_id("event", message.chat_id, message.id, "seed"),
                        type=EventType.MESSAGE_NEW,
                        chat_id=message.chat_id,
                        message=message,
                        actor=self._users.get(message.author_id or ""),
                    )
                )

    @classmethod
    def with_seed_data(cls) -> "MockMaxTransport":
        """Create a deterministic demo dataset for local-first development."""

        account = Account(id="acc_demo", username="demo.max", display_name="Demo MAX User")
        users = [
            User(id="user_alice", username="alice", display_name="Alice Example"),
            User(id="user_bob", username="bob", display_name="Bob Example"),
        ]
        chats = [
            Chat(id="chat_alpha", title="Alpha Team", chat_type=ChatType.GROUP),
            Chat(id="chat_direct", title="Alice", chat_type=ChatType.DIRECT),
        ]
        now = utc_now()
        messages = {
            "chat_alpha": [
                Message(
                    id="m001",
                    chat_id="chat_alpha",
                    author_id="user_alice",
                    text="Morning sync starts in 10 minutes.",
                    created_at=now,
                ),
                Message(
                    id="m002",
                    chat_id="chat_alpha",
                    author_id="user_bob",
                    text="I pushed the archive exporter skeleton.",
                    created_at=now,
                    reply_to_message_id="m001",
                ),
            ],
            "chat_direct": [
                Message(
                    id="m101",
                    chat_id="chat_direct",
                    author_id="user_alice",
                    text="Can we mirror this dialog into Telegram?",
                    created_at=now,
                )
            ],
        }
        return cls(account=account, users=users, chats=chats, messages=messages)

    async def connect(self) -> None:
        """Open the mock transport. No-op for in-memory mode."""

        return None

    async def close(self) -> None:
        """Close the mock transport. No-op for in-memory mode."""

        return None

    async def get_account(self) -> Account | None:
        """Return the seeded demo account."""

        return self._account

    async def get_user(self, user_id: str) -> User | None:
        """Return one seeded user."""

        return self._users.get(user_id)

    async def list_chats(self) -> list[Chat]:
        """Return chats with derived ``last_message_at`` timestamps."""

        chats = list(self._chats.values())
        for chat in chats:
            messages = self._messages.get(chat.id, [])
            if messages:
                latest = max(messages, key=lambda item: item.created_at)
                chat.last_message_at = latest.created_at
        return sorted(chats, key=lambda chat: chat.title.lower())

    async def fetch_history(self, chat_id: str, *, limit: int = 100) -> list[Message]:
        """Return chronologically ordered history for one seeded chat."""

        messages = list(self._messages.get(chat_id, []))
        return sorted(messages, key=lambda item: item.created_at)[-limit:]

    async def iter_updates(self, *, limit: int | None = None) -> AsyncIterator[UpdateEvent]:
        """Yield queued updates in FIFO order."""

        yielded = 0
        while not self._updates.empty():
            if limit is not None and yielded >= limit:
                break
            yielded += 1
            yield await self._updates.get()

    async def send_text_message(
        self, chat_id: str, text: str, *, reply_to_message_id: str | None = None
    ) -> Message:
        """Append an outgoing message and enqueue the corresponding update."""

        message = Message(
            id=stable_id("msg", chat_id, text, utc_now().isoformat()),
            chat_id=chat_id,
            author_id=self._account.id,
            text=text,
            reply_to_message_id=reply_to_message_id,
        )
        self._messages.setdefault(chat_id, []).append(message)
        await self._updates.put(
            UpdateEvent(
                id=stable_id("event", chat_id, message.id, "outgoing"),
                type=EventType.MESSAGE_NEW,
                chat_id=chat_id,
                message=message,
                actor=self._users[self._account.id],
            )
        )
        return message

    async def send_reaction(self, chat_id: str, message_id: str, emoji: str) -> Reaction:
        """Append a reaction to the in-memory message record."""

        reaction = Reaction(emoji=emoji)
        for message in self._messages.get(chat_id, []):
            if message.id == message_id:
                message.reactions.append(reaction)
                break
        return reaction

    async def set_typing(self, chat_id: str, *, enabled: bool) -> TypingStatus:
        """Return a synthetic typing state for the demo account."""

        return TypingStatus(
            chat_id=chat_id,
            user_id=self._account.id,
            expires_at=utc_now() if enabled else None,
        )


def build_max_transport(config: MaxBridgeConfig) -> AbstractMaxTransport:
    """Build an experimental MAX adapter for the current runtime.

    The stable core calls into this helper so adapter selection remains visibly
    separated from storage, bridge, and Telegram concerns.
    """

    adapter = config.experimental.max_adapter
    if adapter == "mock":
        return MockMaxTransport.with_seed_data()
    return UnsupportedMaxTransport()
