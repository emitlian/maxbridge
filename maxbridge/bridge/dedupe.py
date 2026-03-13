"""Dedupe helpers for bridge sync.

The bridge persists dedupe keys in SQLite so repeated sync passes remain
idempotent across process restarts, not just within one in-memory runtime.
"""

from __future__ import annotations

from maxbridge.storage.sqlite import SQLiteStore
from maxbridge.utils.ids import stable_digest


def build_message_dedupe_key(
    *,
    max_chat_id: str,
    max_message_id: str,
    telegram_chat_id: int,
    message_thread_id: int,
) -> str:
    """Build a deterministic dedupe key for one mirrored message."""

    return stable_digest(max_chat_id, max_message_id, telegram_chat_id, message_thread_id)


class DedupeIndex:
    """Persist dedupe keys in the local store."""

    def __init__(self, store: SQLiteStore) -> None:
        self._store = store

    async def seen(self, key: str) -> bool:
        """Return whether a dedupe key is already known."""

        return await self._store.has_dedupe_key(key)

    async def remember(self, key: str, *, scope: str) -> None:
        """Store a dedupe key for future sync passes."""

        await self._store.remember_dedupe_key(key, scope=scope)
