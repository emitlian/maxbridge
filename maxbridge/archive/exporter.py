"""Archive export helpers.

The exporter reads from the stable SQLite store and writes portable artifacts.
It does not depend on a live MAX transport once the local index is populated.
"""

from __future__ import annotations

import shutil
from pathlib import Path

from maxbridge.archive.schema import ArchiveManifest, ChatArchive
from maxbridge.core.exceptions import ArchiveError
from maxbridge.storage.models import ArtifactRecord
from maxbridge.storage.sqlite import SQLiteStore
from maxbridge.utils.ids import stable_id


class ArchiveExporter:
    """Export local data into stable archive artifacts."""

    def __init__(self, store: SQLiteStore, export_dir: str | Path) -> None:
        """Initialize the exporter and ensure the target directory exists."""

        self.store = store
        self.export_dir = Path(export_dir)
        self.export_dir.mkdir(parents=True, exist_ok=True)

    async def export_chat_json(self, chat_id: str) -> Path:
        """Export one chat into a versioned JSON archive file."""

        chat, users, messages = await self.store.collect_chat_bundle(chat_id)
        archive = ChatArchive(chat=chat, users=users, messages=messages)
        target = self.export_dir / f"{chat_id}.json"
        target.write_text(archive.model_dump_json(indent=2), encoding="utf-8")
        await self.store.register_artifact(
            ArtifactRecord(
                id=stable_id("artifact", "chat-json", chat_id),
                kind="chat_json",
                path=str(target),
                chat_id=chat_id,
                metadata={"message_count": len(messages)},
            )
        )
        return target

    async def export_all_json(self) -> list[Path]:
        """Export all locally indexed chats plus a manifest file."""

        paths: list[Path] = []
        chats = await self.store.list_chats()
        total_messages = 0
        for chat in chats:
            # Count messages before writing the manifest so summary output stays
            # independent from any future file write failures.
            total_messages += len(await self.store.get_messages(chat.id, limit=100_000))
            paths.append(await self.export_chat_json(chat.id))
        manifest = ArchiveManifest(
            chat_count=len(chats),
            message_count=total_messages,
            artifact_paths=[str(path) for path in paths],
        )
        manifest_path = self.export_dir / "manifest.json"
        manifest_path.write_text(manifest.model_dump_json(indent=2), encoding="utf-8")
        return paths

    async def export_sqlite_snapshot(self) -> Path:
        """Copy the current SQLite database into the export directory."""

        if not self.store.database_path.exists():
            raise ArchiveError("SQLite database does not exist yet; nothing to snapshot.")
        target = self.export_dir / f"{self.store.database_path.stem}-snapshot.sqlite3"
        shutil.copy2(self.store.database_path, target)
        await self.store.register_artifact(
            ArtifactRecord(
                id=stable_id("artifact", "sqlite-snapshot", str(target)),
                kind="sqlite_snapshot",
                path=str(target),
            )
        )
        return target

    async def stats(self) -> dict[str, int]:
        """Return current SQLite table counts for archive diagnostics."""

        return await self.store.get_stats()
