"""High-level MAXBRIDGE client.

The client is part of the stable core. It orchestrates config loading,
transport lifecycle, local persistence, and event fan-out while keeping the
experimental MAX adapter behind the abstract transport contract.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from pathlib import Path

from maxbridge.config import MaxBridgeConfig, load_config
from maxbridge.core.events import EventBus, EventHandler
from maxbridge.core.models import Account, Chat, Message, Reaction, Session, TypingStatus, UpdateEvent, User
from maxbridge.core.session import SessionManager
from maxbridge.core.transport import AbstractMaxTransport
from maxbridge.experimental.max_adapter import build_max_transport
from maxbridge.storage.sqlite import SQLiteStore
from maxbridge.utils.logging import configure_logging, get_logger

logger = get_logger(__name__)


class MaxBridgeClient:
    """High-level async client for MAXBRIDGE.

    The client intentionally combines three responsibilities:
    - initialize the stable local runtime
    - persist stable state into SQLite
    - delegate MAX-specific operations to an abstract transport

    The transport may be experimental, but the client contract is intended to
    stay stable for callers and for bridge/control-plane code.
    """

    def __init__(
        self,
        *,
        config: MaxBridgeConfig,
        transport: AbstractMaxTransport,
        store: SQLiteStore,
    ) -> None:
        """Initialize the client with explicit dependencies.

        Dependency injection keeps tests and experimental adapters simple. The
        public ``from_config`` constructor remains the common user entry point.
        """

        self.config = config
        self.transport = transport
        self.store = store
        self.events = EventBus()
        self._session_manager = SessionManager(
            session_name=config.core.session_name,
            adapter=config.experimental.max_adapter,
        )
        self._connected = False

    @classmethod
    def from_config(cls, config: str | Path | MaxBridgeConfig) -> "MaxBridgeClient":
        """Create a client from a config path or config object.

        This method wires the stable runtime pieces together:
        config loading, logging, SQLite persistence, and experimental adapter
        selection. The separation is important for honesty and future adapters.
        """

        loaded = load_config(config) if isinstance(config, (str, Path)) else config
        configure_logging(loaded.core.log_level, json_logs=loaded.core.json_logs)
        transport = build_max_transport(loaded)
        store = SQLiteStore(
            loaded.storage.database_path,
            wal_mode=loaded.storage.wal_mode,
            busy_timeout_ms=loaded.storage.sqlite_busy_timeout_ms,
        )
        return cls(config=loaded, transport=transport, store=store)

    async def __aenter__(self) -> "MaxBridgeClient":
        """Support ``async with`` resource management."""

        await self.connect()
        return self

    async def __aexit__(self, *_: object) -> None:
        """Close transport and SQLite resources on context manager exit."""

        await self.close()

    @property
    def session(self) -> Session | None:
        """Return the active session metadata if the client is connected."""

        return self._session_manager.current

    async def connect(self) -> None:
        """Start the stable runtime and open the transport.

        SQLite initialization happens first so that session metadata and later
        events can be persisted even when transport setup fails partway through.
        """

        if self._connected:
            return
        await self.store.initialize()
        await self.transport.connect()
        account = await self.transport.get_account()
        # The stable session record tracks which adapter backed the runtime.
        session = self._session_manager.load_or_create(account.id if account else None)
        await self.store.upsert_session(session)
        self._connected = True
        logger.info("MAXBRIDGE client connected")

    async def close(self) -> None:
        """Close transport and local storage resources."""

        if not self._connected:
            return
        await self.transport.close()
        await self.store.close()
        self._connected = False
        logger.info("MAXBRIDGE client closed")

    def on_event(self, handler: EventHandler) -> EventHandler:
        """Register an event handler on the in-process event bus."""

        return self.events.register(handler)

    async def get_account(self) -> Account | None:
        """Return the current account when the transport supports it."""

        return await self.transport.get_account()

    async def get_user(self, user_id: str) -> User | None:
        """Fetch and locally cache one user record."""

        user = await self.transport.get_user(user_id)
        if user is not None:
            await self.store.upsert_user(user)
        return user

    async def get_chats(self) -> list[Chat]:
        """Fetch chats from the transport and persist them locally."""

        chats = await self.transport.list_chats()
        for chat in chats:
            await self.store.upsert_chat(chat)
        return chats

    async def get_history(self, chat_id: str, *, limit: int = 100) -> list[Message]:
        """Fetch message history and persist both messages and known authors."""

        messages = await self.transport.fetch_history(chat_id, limit=limit)
        for message in messages:
            await self.store.upsert_message(message)
            if message.author_id:
                await self.get_user(message.author_id)
        return messages

    async def iter_events(self, *, limit: int | None = None) -> AsyncIterator[UpdateEvent]:
        """Yield transport events after persisting them to stable storage."""

        async for event in self.transport.iter_updates(limit=limit):
            await self._persist_event(event)
            await self.events.emit(event)
            yield event

    async def send_text_message(
        self, chat_id: str, text: str, *, reply_to_message_id: str | None = None
    ) -> Message:
        """Send a text message through the transport and persist the result."""

        message = await self.transport.send_text_message(
            chat_id, text, reply_to_message_id=reply_to_message_id
        )
        await self.store.upsert_message(message)
        return message

    async def send_reaction(self, chat_id: str, message_id: str, emoji: str) -> Reaction:
        """Send a reaction through the underlying transport."""

        return await self.transport.send_reaction(chat_id, message_id, emoji)

    async def set_typing(self, chat_id: str, *, enabled: bool) -> TypingStatus:
        """Toggle a typing indicator through the underlying transport."""

        return await self.transport.set_typing(chat_id, enabled=enabled)

    async def _persist_event(self, event: UpdateEvent) -> None:
        """Persist event side effects before exposing the event to callers.

        The stable core uses SQLite as the source of truth for later archive,
        replay, bridge, and diagnostic flows. Persisting first makes those
        paths deterministic even when user callbacks fail.
        """

        if event.actor is not None:
            await self.store.upsert_user(event.actor)
        if event.message is not None:
            await self.store.upsert_message(event.message)
        if event.cursor is not None:
            await self.store.set_sync_cursor("updates", event.cursor)
