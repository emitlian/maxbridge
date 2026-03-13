from __future__ import annotations

from pathlib import Path

import pytest

from maxbridge.archive.exporter import ArchiveExporter
from maxbridge.core.models import Chat, ChatType, Message, User
from maxbridge.storage.sqlite import SQLiteStore


@pytest.mark.asyncio
async def test_export_chat_json(tmp_path: Path) -> None:
    """A chat indexed in SQLite should export into a JSON archive file."""

    store = SQLiteStore(tmp_path / "maxbridge.db")
    await store.initialize()
    await store.upsert_chat(Chat(id="chat_1", title="General", chat_type=ChatType.GROUP))
    await store.upsert_user(User(id="user_1", display_name="Alice"))
    await store.upsert_message(
        Message(id="msg_1", chat_id="chat_1", author_id="user_1", text="hello")
    )

    exporter = ArchiveExporter(store, tmp_path / "exports")
    path = await exporter.export_chat_json("chat_1")

    assert path.exists()
    assert "\"chat_1\"" in path.read_text(encoding="utf-8")

    await store.close()
