from __future__ import annotations

from pathlib import Path

import pytest

from maxbridge.bridge.formatter import TelegramMirrorFormatter
from maxbridge.bridge.routing import RoutingPolicy
from maxbridge.bridge.sync_engine import BridgeSyncEngine
from maxbridge.config.models import MaxBridgeConfig
from maxbridge.core.client import MaxBridgeClient
from maxbridge.experimental.max_adapter import MockMaxTransport
from maxbridge.storage.sqlite import SQLiteStore


class RecordingGateway:
    """Minimal Telegram gateway stub that records bridge writes for assertions."""

    def __init__(self) -> None:
        self.created_topics: list[tuple[int, str]] = []
        self.sent_messages: list[dict[str, object]] = []

    async def create_topic(self, chat_id: int, title: str) -> int:
        """Return a deterministic topic ID while recording the request."""

        self.created_topics.append((chat_id, title))
        return 777

    async def send_message(
        self,
        chat_id: int,
        thread_id: int,
        text: str,
        *,
        reply_to_message_id: int | None = None,
    ) -> int:
        """Record outgoing Telegram messages and return deterministic IDs."""

        message_id = 100 + len(self.sent_messages)
        self.sent_messages.append(
            {
                "chat_id": chat_id,
                "thread_id": thread_id,
                "text": text,
                "reply_to_message_id": reply_to_message_id,
                "message_id": message_id,
            }
        )
        return message_id


@pytest.mark.asyncio
async def test_sync_engine_preserves_reply_chain(tmp_path: Path) -> None:
    """Reply mappings should become Telegram reply targets on later messages."""

    config = MaxBridgeConfig.model_validate(
        {
            "storage": {"database_path": str(tmp_path / "maxbridge.db")},
            "bridge": {"enabled": True, "dry_run": True, "selected_chat_ids": ["chat_alpha"]},
            "telegram": {"default_forum_chat_id": -1001234567890},
        }
    )
    store = SQLiteStore(config.storage.database_path)
    transport = MockMaxTransport.with_seed_data()
    client = MaxBridgeClient(config=config, transport=transport, store=store)
    await client.connect()

    gateway = RecordingGateway()
    engine = BridgeSyncEngine(
        client=client,
        store=client.store,
        gateway=gateway,
        routing=RoutingPolicy(client.config.bridge),
        formatter=TelegramMirrorFormatter(client.config.bridge),
    )

    chats = {chat.id: chat for chat in await client.get_chats()}
    messages = await client.get_history("chat_alpha", limit=10)
    first, second = messages

    first_result = await engine.sync_message(chats["chat_alpha"], first)
    second_result = await engine.sync_message(chats["chat_alpha"], second)

    assert first_result == 100
    assert second_result == 101
    assert gateway.created_topics == [(-1001234567890, "Alpha Team")]
    assert gateway.sent_messages[0]["reply_to_message_id"] is None
    assert gateway.sent_messages[1]["reply_to_message_id"] == 100

    await client.close()
