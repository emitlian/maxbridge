from __future__ import annotations

from pathlib import Path

import pytest

from maxbridge.core.models import Chat, ChatType, Message, TopicBinding, User
from maxbridge.storage.sqlite import SQLiteStore


@pytest.mark.asyncio
async def test_sqlite_store_roundtrip(tmp_path: Path) -> None:
    """Core SQLite entities should round-trip through the stable store."""

    store = SQLiteStore(tmp_path / "maxbridge.db")
    await store.initialize()

    chat = Chat(id="chat_1", title="General", chat_type=ChatType.GROUP)
    user = User(id="user_1", display_name="Alice")
    message = Message(id="msg_1", chat_id="chat_1", author_id="user_1", text="hello")
    binding = TopicBinding(
        id="topic_1",
        max_chat_id="chat_1",
        telegram_chat_id=-100123,
        message_thread_id=42,
        topic_title="General",
    )

    await store.upsert_chat(chat)
    await store.upsert_user(user)
    await store.upsert_message(message)
    await store.set_topic_binding(binding)

    assert await store.get_chat("chat_1") is not None
    assert await store.get_user("user_1") is not None
    assert len(await store.get_messages("chat_1")) == 1
    assert await store.get_topic_binding("chat_1") is not None

    await store.close()
