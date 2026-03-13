"""Archive import helpers.

The importer restores versioned JSON archive payloads into the local SQLite
index. It does not attempt to write data back into MAX itself.
"""

from __future__ import annotations

from pathlib import Path

from maxbridge.archive.schema import ChatArchive
from maxbridge.storage.sqlite import SQLiteStore


class ArchiveImporter:
    """Import JSON archives into the local storage index."""

    def __init__(self, store: SQLiteStore) -> None:
        """Create an importer backed by the stable SQLite store."""

        self.store = store

    async def import_chat_json(self, path: str | Path) -> ChatArchive:
        """Import one chat archive JSON file into the local index."""

        archive = ChatArchive.model_validate_json(Path(path).read_text(encoding="utf-8"))
        await self.store.upsert_chat(archive.chat)
        for user in archive.users:
            await self.store.upsert_user(user)
        for message in archive.messages:
            await self.store.upsert_message(message)
        return archive
