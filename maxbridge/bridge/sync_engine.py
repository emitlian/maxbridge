"""Bridge sync engine.

The sync engine is the core of the stable mirror path. It translates locally
indexed MAX messages into Telegram forum messages, ensures bindings exist,
records message mappings, and preserves reply chains when possible.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from maxbridge.bridge.bindings import build_bridge_binding, build_topic_binding
from maxbridge.bridge.dedupe import DedupeIndex, build_message_dedupe_key
from maxbridge.bridge.formatter import TelegramMirrorFormatter
from maxbridge.bridge.routing import RoutingPolicy
from maxbridge.core.exceptions import BridgeBindingError
from maxbridge.core.models import Chat, Message, TopicBinding
from maxbridge.storage.models import MessageMappingRecord
from maxbridge.storage.sqlite import SQLiteStore
from maxbridge.utils.ids import stable_id
from maxbridge.utils.time import utc_now

if TYPE_CHECKING:
    from maxbridge.core.client import MaxBridgeClient
    from maxbridge.telegram.forum import TelegramForumGateway


class BridgeSyncEngine:
    """Synchronize MAX history into Telegram forum topics."""

    def __init__(
        self,
        *,
        client: "MaxBridgeClient",
        store: SQLiteStore,
        gateway: "TelegramForumGateway",
        routing: RoutingPolicy,
        formatter: TelegramMirrorFormatter,
    ) -> None:
        """Initialize the sync engine with explicit collaborators.

        The engine works only with stable abstractions: the client, SQLite
        store, routing policy, formatter, and Telegram gateway.
        """

        self.client = client
        self.store = store
        self.gateway = gateway
        self.routing = routing
        self.formatter = formatter
        self.dedupe = DedupeIndex(store)

    async def ensure_topic_binding(self, chat: Chat) -> TopicBinding | None:
        """Return or create the Telegram topic binding for one MAX chat.

        The binding model is intentionally strict: one MAX chat maps to exactly
        one Telegram forum topic. That keeps replay and message mapping logic
        deterministic and easy to inspect.
        """

        existing = await self.store.get_topic_binding(chat.id)
        if existing is not None and existing.enabled:
            return existing

        forum_chat_id = self.client.config.telegram.default_forum_chat_id
        if forum_chat_id is None:
            # A missing forum target is not an error for every caller. Some
            # paths may intentionally inspect bridge state before configuration.
            return None
        if not self.client.config.bridge.create_topics:
            raise BridgeBindingError(
                f"No topic binding for {chat.id} and auto topic creation is disabled."
            )

        thread_id = await self.gateway.create_topic(forum_chat_id, chat.title)
        topic_binding = build_topic_binding(
            max_chat_id=chat.id,
            telegram_chat_id=forum_chat_id,
            message_thread_id=thread_id,
            topic_title=chat.title,
        )
        await self.store.set_topic_binding(topic_binding)
        await self.store.set_bridge_binding(build_bridge_binding(topic_binding=topic_binding))
        return topic_binding

    async def sync_message(self, chat: Chat, message: Message) -> int | None:
        """Mirror one message into Telegram and persist the resulting mapping.

        Return value semantics:
        - integer Telegram message ID when a mirror write happened
        - existing Telegram message ID when the mapping was already stored
        - ``None`` when routing, configuration, or dedupe prevented a write
        """

        decision = self.routing.should_sync(chat.id, is_system=message.is_system)
        if not decision.allowed:
            return None

        existing_mapping = await self.store.get_message_mapping(chat.id, message.id)
        if existing_mapping is not None:
            # Returning the stored Telegram message ID makes repeated sync passes
            # easy to reason about for callers and tests.
            return existing_mapping.telegram_message_id

        binding = await self.ensure_topic_binding(chat)
        if binding is None:
            return None

        dedupe_key = build_message_dedupe_key(
            max_chat_id=chat.id,
            max_message_id=message.id,
            telegram_chat_id=binding.telegram_chat_id,
            message_thread_id=binding.message_thread_id,
        )
        if await self.dedupe.seen(dedupe_key):
            return None

        author = await self.client.get_user(message.author_id) if message.author_id else None
        formatted = self.formatter.format(chat=chat, message=message, author=author)
        reply_to_telegram_message_id: int | None = None
        if message.reply_to_message_id:
            # Reply preservation depends on the parent message having a stored
            # Telegram mapping from an earlier or the current sync pass.
            reply_mapping = await self.store.get_message_mapping(chat.id, message.reply_to_message_id)
            if reply_mapping is not None:
                reply_to_telegram_message_id = reply_mapping.telegram_message_id
        telegram_message_id = await self.gateway.send_message(
            binding.telegram_chat_id,
            binding.message_thread_id,
            formatted,
            reply_to_message_id=reply_to_telegram_message_id,
        )

        mapping = MessageMappingRecord(
            id=stable_id("map", chat.id, message.id, telegram_message_id),
            max_chat_id=chat.id,
            max_message_id=message.id,
            telegram_chat_id=binding.telegram_chat_id,
            telegram_message_id=telegram_message_id,
            message_thread_id=binding.message_thread_id,
        )
        await self.store.record_message_mapping(mapping)
        await self.dedupe.remember(dedupe_key, scope="max_to_telegram")
        # ``last_synced_at`` is useful for status pages and later recovery logic.
        await self.store.set_topic_binding(
            binding.model_copy(update={"last_synced_at": utc_now()})
        )
        return telegram_message_id
