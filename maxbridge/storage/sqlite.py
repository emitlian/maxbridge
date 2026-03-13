"""SQLite storage backend for MAXBRIDGE.

The storage layer is a stable part of the project. It keeps local state for:
- session metadata
- normalized chats, users, and messages
- bridge bindings and topic bindings
- MAX-to-Telegram message mappings
- sync cursors, dedupe keys, audit trails, and archive artifacts

SQLite is intentionally used as the local source of truth for bridge recovery,
archive export, dry-run inspection, and operational debugging.
"""

from __future__ import annotations

import json
from importlib import resources
from pathlib import Path
from typing import Any

import aiosqlite

from maxbridge.core.exceptions import StorageError
from maxbridge.core.models import Chat, Message, Session, TopicBinding, User
from maxbridge.storage.models import (
    ArtifactRecord,
    AuditLogRecord,
    BridgeBindingRecord,
    CommandHistoryRecord,
    MessageMappingRecord,
)
from maxbridge.utils.time import utc_now

try:
    import orjson
except ImportError:  # pragma: no cover
    orjson = None


class SQLiteStore:
    """Persistent local store backed by SQLite.

    This class prefers explicit upsert methods over generic row helpers so that
    each persistence path can document its own invariants and edge cases.
    """

    def __init__(self, database_path: str | Path, *, wal_mode: bool = True, busy_timeout_ms: int = 5000) -> None:
        """Initialize the store with filesystem and SQLite tuning settings."""

        self.database_path = Path(database_path)
        self.wal_mode = wal_mode
        self.busy_timeout_ms = busy_timeout_ms
        self._connection: aiosqlite.Connection | None = None

    async def initialize(self) -> None:
        """Open the SQLite connection and apply bundled migrations.

        WAL mode is enabled by default because bridge and control-plane flows
        benefit from resilient writes while readers inspect the same database.
        """

        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._connection = await aiosqlite.connect(self.database_path)
        self._connection.row_factory = aiosqlite.Row
        await self._connection.execute(f"PRAGMA busy_timeout = {self.busy_timeout_ms}")
        await self._connection.execute("PRAGMA foreign_keys = ON")
        if self.wal_mode:
            await self._connection.execute("PRAGMA journal_mode = WAL")
        # Migration bookkeeping is stored separately from domain tables so the
        # bundled SQL files remain append-only and easy to reason about.
        await self._connection.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version TEXT PRIMARY KEY,
                applied_at TEXT NOT NULL
            )
            """
        )
        await self._apply_migrations()
        await self._connection.commit()

    async def close(self) -> None:
        """Close the active SQLite connection if one exists."""

        if self._connection is not None:
            await self._connection.close()
            self._connection = None

    async def upsert_session(self, session: Session) -> None:
        """Insert or update stable session metadata."""

        db = self._db()
        await db.execute(
            """
            INSERT INTO sessions (session_id, account_id, adapter, created_at, updated_at, metadata_json)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(session_id) DO UPDATE SET
                account_id = excluded.account_id,
                adapter = excluded.adapter,
                updated_at = excluded.updated_at,
                metadata_json = excluded.metadata_json
            """,
            (
                session.id,
                session.account_id,
                session.adapter,
                session.created_at.isoformat(),
                session.updated_at.isoformat(),
                _json_dump(session.metadata),
            ),
        )
        await db.commit()

    async def upsert_user(self, user: User) -> None:
        """Insert or update a cached user record.

        User records are duplicated in raw JSON form so later archive/export
        logic can reconstruct the original typed model without join logic.
        """

        db = self._db()
        raw_json = user.model_dump_json()
        await db.execute(
            """
            INSERT INTO users (user_id, username, display_name, is_bot, raw_json, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                username = excluded.username,
                display_name = excluded.display_name,
                is_bot = excluded.is_bot,
                raw_json = excluded.raw_json,
                updated_at = excluded.updated_at
            """,
            (
                user.id,
                user.username,
                user.display_name,
                int(user.is_bot),
                raw_json,
                utc_now().isoformat(),
            ),
        )
        await db.commit()

    async def get_user(self, user_id: str) -> User | None:
        """Load one cached user from SQLite."""

        db = self._db()
        cursor = await db.execute("SELECT raw_json FROM users WHERE user_id = ?", (user_id,))
        row = await cursor.fetchone()
        return User.model_validate_json(row["raw_json"]) if row else None

    async def upsert_chat(self, chat: Chat) -> None:
        """Insert or update a cached chat record."""

        db = self._db()
        raw_json = chat.model_dump_json()
        await db.execute(
            """
            INSERT INTO chats (chat_id, title, chat_type, is_archived, last_message_at, raw_json, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(chat_id) DO UPDATE SET
                title = excluded.title,
                chat_type = excluded.chat_type,
                is_archived = excluded.is_archived,
                last_message_at = excluded.last_message_at,
                raw_json = excluded.raw_json,
                updated_at = excluded.updated_at
            """,
            (
                chat.id,
                chat.title,
                chat.chat_type.value,
                int(chat.is_archived),
                chat.last_message_at.isoformat() if chat.last_message_at else None,
                raw_json,
                utc_now().isoformat(),
            ),
        )
        await db.commit()

    async def list_chats(self) -> list[Chat]:
        """List cached chats ordered by title for predictable CLI output."""

        db = self._db()
        cursor = await db.execute("SELECT raw_json FROM chats ORDER BY title ASC")
        rows = await cursor.fetchall()
        return [Chat.model_validate_json(row["raw_json"]) for row in rows]

    async def get_chat(self, chat_id: str) -> Chat | None:
        """Load one cached chat by ID."""

        db = self._db()
        cursor = await db.execute("SELECT raw_json FROM chats WHERE chat_id = ?", (chat_id,))
        row = await cursor.fetchone()
        return Chat.model_validate_json(row["raw_json"]) if row else None

    async def upsert_message(self, message: Message) -> None:
        """Insert or update a message in the local history index.

        Message identity is scoped by ``chat_id`` and ``message_id`` because
        upstream systems commonly reuse message IDs across chats.
        """

        db = self._db()
        raw_json = message.model_dump_json()
        await db.execute(
            """
            INSERT INTO messages (
                chat_id, message_id, author_id, text, created_at, edited_at,
                reply_to_message_id, thread_id, is_system, raw_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(chat_id, message_id) DO UPDATE SET
                author_id = excluded.author_id,
                text = excluded.text,
                edited_at = excluded.edited_at,
                reply_to_message_id = excluded.reply_to_message_id,
                thread_id = excluded.thread_id,
                is_system = excluded.is_system,
                raw_json = excluded.raw_json
            """,
            (
                message.chat_id,
                message.id,
                message.author_id,
                message.text,
                message.created_at.isoformat(),
                message.edited_at.isoformat() if message.edited_at else None,
                message.reply_to_message_id,
                message.thread_id,
                int(message.is_system),
                raw_json,
            ),
        )
        await db.commit()

    async def get_messages(self, chat_id: str, *, limit: int = 100) -> list[Message]:
        """Load chronologically ordered messages for one chat."""

        db = self._db()
        cursor = await db.execute(
            """
            SELECT raw_json
            FROM messages
            WHERE chat_id = ?
            ORDER BY created_at ASC
            LIMIT ?
            """,
            (chat_id, limit),
        )
        rows = await cursor.fetchall()
        return [Message.model_validate_json(row["raw_json"]) for row in rows]

    async def collect_chat_bundle(self, chat_id: str) -> tuple[Chat, list[User], list[Message]]:
        """Collect the minimal archive bundle for one chat.

        The method walks message authors to build a stable export payload
        without requiring a separate participant table in the MVP schema.
        """

        chat = await self.get_chat(chat_id)
        if chat is None:
            raise StorageError(f"Chat not found: {chat_id}")
        messages = await self.get_messages(chat_id, limit=100_000)
        users: list[User] = []
        seen: set[str] = set()
        for message in messages:
            # Archive exports only need one copy of each known author.
            if not message.author_id or message.author_id in seen:
                continue
            user = await self.get_user(message.author_id)
            if user is not None:
                users.append(user)
                seen.add(user.id)
        return chat, users, messages

    async def set_bridge_binding(self, binding: BridgeBindingRecord) -> None:
        """Persist a bridge binding record.

        Bridge bindings describe the logical routing target for a MAX chat.
        Topic bindings carry the more specific Telegram thread information.
        """

        db = self._db()
        await db.execute(
            """
            INSERT INTO bridge_bindings (
                binding_id, source_chat_id, target_chat_id, enabled,
                topic_binding_id, created_at, raw_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(binding_id) DO UPDATE SET
                source_chat_id = excluded.source_chat_id,
                target_chat_id = excluded.target_chat_id,
                enabled = excluded.enabled,
                topic_binding_id = excluded.topic_binding_id,
                raw_json = excluded.raw_json
            """,
            (
                binding.id,
                binding.source_chat_id,
                binding.target_chat_id,
                int(binding.enabled),
                binding.topic_binding_id,
                binding.created_at.isoformat(),
                binding.model_dump_json(),
            ),
        )
        await db.commit()

    async def set_topic_binding(self, binding: TopicBinding) -> None:
        """Persist the concrete Telegram forum topic binding for one MAX chat."""

        db = self._db()
        await db.execute(
            """
            INSERT INTO topic_bindings (
                binding_id, max_chat_id, telegram_chat_id, message_thread_id,
                topic_title, enabled, last_synced_at, created_at, raw_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(binding_id) DO UPDATE SET
                max_chat_id = excluded.max_chat_id,
                telegram_chat_id = excluded.telegram_chat_id,
                message_thread_id = excluded.message_thread_id,
                topic_title = excluded.topic_title,
                enabled = excluded.enabled,
                last_synced_at = excluded.last_synced_at,
                raw_json = excluded.raw_json
            """,
            (
                binding.id,
                binding.max_chat_id,
                binding.telegram_chat_id,
                binding.message_thread_id,
                binding.topic_title,
                int(binding.enabled),
                binding.last_synced_at.isoformat() if binding.last_synced_at else None,
                binding.created_at.isoformat(),
                binding.model_dump_json(),
            ),
        )
        await db.commit()

    async def get_topic_binding(self, chat_id: str) -> TopicBinding | None:
        """Return the active topic binding for one MAX chat."""

        db = self._db()
        cursor = await db.execute(
            "SELECT raw_json FROM topic_bindings WHERE max_chat_id = ? AND enabled = 1",
            (chat_id,),
        )
        row = await cursor.fetchone()
        return TopicBinding.model_validate_json(row["raw_json"]) if row else None

    async def list_topic_bindings(self) -> list[TopicBinding]:
        """List all stored topic bindings."""

        db = self._db()
        cursor = await db.execute("SELECT raw_json FROM topic_bindings ORDER BY created_at ASC")
        rows = await cursor.fetchall()
        return [TopicBinding.model_validate_json(row["raw_json"]) for row in rows]

    async def disable_topic_binding(self, chat_id: str) -> None:
        """Soft-disable a topic binding instead of deleting it.

        Keeping disabled bindings is useful for auditability and future
        recovery tooling, even though the MVP does not expose restore flows yet.
        """

        db = self._db()
        cursor = await db.execute(
            "SELECT raw_json FROM topic_bindings WHERE max_chat_id = ?",
            (chat_id,),
        )
        row = await cursor.fetchone()
        if row is None:
            return
        binding = TopicBinding.model_validate_json(row["raw_json"]).model_copy(update={"enabled": False})
        await self.set_topic_binding(binding)

    async def record_message_mapping(self, mapping: MessageMappingRecord) -> None:
        """Persist a MAX-to-Telegram message mapping.

        These mappings are the basis for idempotent bridge runs and for mapping
        reply chains from MAX messages onto Telegram replies.
        """

        db = self._db()
        await db.execute(
            """
            INSERT INTO message_mappings (
                mapping_id, max_chat_id, max_message_id, telegram_chat_id, telegram_message_id,
                message_thread_id, direction, created_at, raw_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(mapping_id) DO UPDATE SET
                telegram_message_id = excluded.telegram_message_id,
                raw_json = excluded.raw_json
            """,
            (
                mapping.id,
                mapping.max_chat_id,
                mapping.max_message_id,
                mapping.telegram_chat_id,
                mapping.telegram_message_id,
                mapping.message_thread_id,
                mapping.direction,
                mapping.created_at.isoformat(),
                mapping.model_dump_json(),
            ),
        )
        await db.commit()

    async def get_message_mapping(self, chat_id: str, message_id: str) -> MessageMappingRecord | None:
        """Return one stored MAX-to-Telegram mapping when it exists."""

        db = self._db()
        cursor = await db.execute(
            """
            SELECT raw_json
            FROM message_mappings
            WHERE max_chat_id = ? AND max_message_id = ? AND direction = 'max_to_telegram'
            """,
            (chat_id, message_id),
        )
        row = await cursor.fetchone()
        return MessageMappingRecord.model_validate_json(row["raw_json"]) if row else None

    async def list_message_mappings(
        self, *, chat_id: str | None = None, limit: int = 100
    ) -> list[MessageMappingRecord]:
        """List stored message mappings for diagnostics and demo inspection."""

        db = self._db()
        if chat_id is None:
            cursor = await db.execute(
                """
                SELECT raw_json
                FROM message_mappings
                ORDER BY created_at ASC
                LIMIT ?
                """,
                (limit,),
            )
        else:
            cursor = await db.execute(
                """
                SELECT raw_json
                FROM message_mappings
                WHERE max_chat_id = ?
                ORDER BY created_at ASC
                LIMIT ?
                """,
                (chat_id, limit),
            )
        rows = await cursor.fetchall()
        return [MessageMappingRecord.model_validate_json(row["raw_json"]) for row in rows]

    async def set_sync_cursor(self, stream_name: str, cursor_value: str) -> None:
        """Persist a cursor for a named update stream.

        Cursor storage is intentionally generic because replay, polling, and
        future adapters may expose different cursor semantics.
        """

        db = self._db()
        await db.execute(
            """
            INSERT INTO sync_cursors (stream_name, cursor, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(stream_name) DO UPDATE SET
                cursor = excluded.cursor,
                updated_at = excluded.updated_at
            """,
            (stream_name, cursor_value, utc_now().isoformat()),
        )
        await db.commit()

    async def get_sync_cursor(self, stream_name: str) -> str | None:
        """Return the stored cursor for one stream, if any."""

        db = self._db()
        cursor = await db.execute(
            "SELECT cursor FROM sync_cursors WHERE stream_name = ?",
            (stream_name,),
        )
        row = await cursor.fetchone()
        return str(row["cursor"]) if row else None

    async def register_artifact(self, artifact: ArtifactRecord) -> None:
        """Register an archive artifact in the local catalog."""

        db = self._db()
        await db.execute(
            """
            INSERT INTO artifacts (artifact_id, kind, path, chat_id, created_at, metadata_json, raw_json)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(artifact_id) DO UPDATE SET
                path = excluded.path,
                metadata_json = excluded.metadata_json,
                raw_json = excluded.raw_json
            """,
            (
                artifact.id,
                artifact.kind,
                artifact.path,
                artifact.chat_id,
                artifact.created_at.isoformat(),
                _json_dump(artifact.metadata),
                artifact.model_dump_json(),
            ),
        )
        await db.commit()

    async def audit(self, record: AuditLogRecord) -> None:
        """Append one audit record.

        Audit records are intentionally append-only. This keeps the operator
        history understandable when bridge actions are triggered from Telegram.
        """

        db = self._db()
        await db.execute(
            """
            INSERT INTO audit_log (event_id, actor, action, target, details_json, created_at, raw_json)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record.id,
                record.actor,
                record.action,
                record.target,
                _json_dump(record.details),
                record.created_at.isoformat(),
                record.model_dump_json(),
            ),
        )
        await db.commit()

    async def record_command(self, record: CommandHistoryRecord) -> None:
        """Append one command execution record."""

        db = self._db()
        await db.execute(
            """
            INSERT INTO command_history (
                command_id, source, actor, command, arguments_json, status, created_at, raw_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record.id,
                record.source,
                record.actor,
                record.command,
                _json_dump(record.arguments),
                record.status,
                record.created_at.isoformat(),
                record.model_dump_json(),
            ),
        )
        await db.commit()

    async def has_dedupe_key(self, key: str) -> bool:
        """Check whether a dedupe key was already observed."""

        db = self._db()
        cursor = await db.execute(
            "SELECT 1 FROM dedupe_hashes WHERE dedupe_key = ?",
            (key,),
        )
        return await cursor.fetchone() is not None

    async def remember_dedupe_key(
        self, key: str, *, scope: str, metadata: dict[str, Any] | None = None
    ) -> None:
        """Persist a dedupe key if it has not been seen before."""

        db = self._db()
        await db.execute(
            """
            INSERT OR IGNORE INTO dedupe_hashes (dedupe_key, scope, first_seen_at, metadata_json)
            VALUES (?, ?, ?, ?)
            """,
            (key, scope, utc_now().isoformat(), _json_dump(metadata or {})),
        )
        await db.commit()

    async def get_stats(self) -> dict[str, int]:
        """Return lightweight table counts for diagnostics and health checks."""

        db = self._db()
        tables = [
            "sessions",
            "users",
            "chats",
            "messages",
            "bridge_bindings",
            "topic_bindings",
            "message_mappings",
            "artifacts",
            "audit_log",
            "command_history",
        ]
        stats: dict[str, int] = {}
        for table in tables:
            # Table names are hard-coded above, so formatting SQL here is safe.
            cursor = await db.execute(f"SELECT COUNT(*) AS count FROM {table}")
            row = await cursor.fetchone()
            stats[table] = int(row["count"])
        return stats

    async def _apply_migrations(self) -> None:
        """Apply bundled SQL migrations exactly once per version."""

        db = self._db()
        applied_cursor = await db.execute("SELECT version FROM schema_migrations")
        applied = {row["version"] for row in await applied_cursor.fetchall()}
        migration_dir = resources.files("maxbridge.storage.migrations")
        for item in sorted(migration_dir.iterdir(), key=lambda path: path.name):
            if item.suffix != ".sql" or item.name in applied:
                continue
            # Migrations are kept as ordered SQL files to stay reviewable.
            sql = item.read_text(encoding="utf-8")
            await db.executescript(sql)
            await db.execute(
                "INSERT INTO schema_migrations (version, applied_at) VALUES (?, ?)",
                (item.name, utc_now().isoformat()),
            )

    def _db(self) -> aiosqlite.Connection:
        """Return the active SQLite connection or raise a clear error."""

        if self._connection is None:
            raise StorageError("SQLite store is not initialized")
        return self._connection


def _json_dump(value: Any) -> str:
    """Serialize JSON with ``orjson`` when available, else fall back to stdlib."""

    if orjson is not None:
        return orjson.dumps(value).decode("utf-8")
    return json.dumps(value, ensure_ascii=False)
