"""Bridge manager and orchestration.

The manager exposes the stable operational entry points used by the CLI and
Telegram control plane. It keeps the vertical slice understandable:
bind a chat, run a sync pass, inspect mappings, repeat safely.
"""

from __future__ import annotations

import asyncio

from maxbridge.bridge.bindings import build_bridge_binding, build_topic_binding
from maxbridge.bridge.formatter import TelegramMirrorFormatter
from maxbridge.bridge.routing import RoutingPolicy
from maxbridge.bridge.sync_engine import BridgeSyncEngine
from maxbridge.core.models import TopicBinding
from maxbridge.telegram.forum import TelegramForumGateway
from maxbridge.utils.logging import get_logger

logger = get_logger(__name__)


class BridgeManager:
    """Manage MAX-to-Telegram mirror flows.

    The manager intentionally stays thin. Higher-level control surfaces should
    call into this class rather than duplicating routing or binding logic.
    """

    def __init__(self, client, gateway: TelegramForumGateway) -> None:
        """Create a bridge manager for one client runtime."""

        self.client = client
        self.gateway = gateway
        self.routing = RoutingPolicy(client.config.bridge)
        self.formatter = TelegramMirrorFormatter(client.config.bridge)
        self.engine = BridgeSyncEngine(
            client=client,
            store=client.store,
            gateway=gateway,
            routing=self.routing,
            formatter=self.formatter,
        )
        self._paused = False

    @property
    def paused(self) -> bool:
        """Expose the current pause state for status views."""

        return self._paused

    async def sync_once(self) -> int:
        """Run one end-to-end mirror pass across eligible chats."""

        if self._paused:
            return 0
        mirrored = 0
        chats = await self.client.get_chats()
        for chat in chats:
            decision = self.routing.should_sync(chat.id)
            if not decision.allowed:
                logger.debug("Skipping chat %s: %s", chat.id, decision.reason)
                continue
            # History is loaded from the transport, then each message is handed
            # to the sync engine for mapping, dedupe, and Telegram delivery.
            messages = await self.client.get_history(
                chat.id, limit=self.client.config.core.max_batch_size
            )
            for message in messages:
                result = await self.engine.sync_message(chat, message)
                if result is not None:
                    mirrored += 1
        return mirrored

    async def run_forever(self) -> None:
        """Run the bridge in polling mode.

        The MVP uses periodic sync passes because they are easy to replay and
        test even before a real streaming MAX adapter exists.
        """

        while True:
            try:
                await self.sync_once()
            finally:
                await asyncio.sleep(self.client.config.core.poll_interval_seconds)

    async def bind_chat(
        self,
        *,
        max_chat_id: str,
        telegram_chat_id: int,
        message_thread_id: int,
        topic_title: str | None = None,
    ) -> TopicBinding:
        """Persist a direct chat-to-topic binding."""

        title = topic_title or max_chat_id
        binding = build_topic_binding(
            max_chat_id=max_chat_id,
            telegram_chat_id=telegram_chat_id,
            message_thread_id=message_thread_id,
            topic_title=title,
        )
        await self.client.store.set_topic_binding(binding)
        await self.client.store.set_bridge_binding(build_bridge_binding(topic_binding=binding))
        return binding

    async def auto_bind_chat(
        self,
        *,
        max_chat_id: str,
        telegram_chat_id: int | None = None,
        topic_title: str | None = None,
    ) -> TopicBinding:
        """Create a forum topic through Telegram and persist the new binding."""

        forum_chat_id = telegram_chat_id or self.client.config.telegram.default_forum_chat_id
        if forum_chat_id is None:
            raise ValueError("default_forum_chat_id is not configured")
        thread_id = await self.gateway.create_topic(forum_chat_id, topic_title or max_chat_id)
        return await self.bind_chat(
            max_chat_id=max_chat_id,
            telegram_chat_id=forum_chat_id,
            message_thread_id=thread_id,
            topic_title=topic_title or max_chat_id,
        )

    async def unbind_chat(self, max_chat_id: str) -> None:
        """Disable a binding without deleting its historical record."""

        await self.client.store.disable_topic_binding(max_chat_id)

    async def status(self) -> dict[str, object]:
        """Return lightweight bridge status for CLI and bot diagnostics."""

        bindings = await self.client.store.list_topic_bindings()
        mappings = await self.client.store.list_message_mappings(limit=10_000)
        return {
            "enabled": self.client.config.bridge.enabled,
            "dry_run": self.client.config.bridge.dry_run,
            "paused": self._paused,
            "bindings": len(bindings),
            "message_mappings": len(mappings),
        }

    def pause(self) -> None:
        """Pause future sync passes."""

        self._paused = True

    def resume(self) -> None:
        """Resume future sync passes."""

        self._paused = False
