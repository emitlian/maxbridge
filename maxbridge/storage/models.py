"""Storage record models.

These models mirror rows stored in the SQLite layer. They are intentionally
separate from the higher-level domain models so that persistence concerns such
as mappings, audit entries, and artifact registries remain explicit.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from maxbridge.utils.time import utc_now


class Record(BaseModel):
    """Base model for SQLite-backed records."""

    model_config = ConfigDict(extra="forbid")


class BridgeBindingRecord(Record):
    """Persistent bridge binding between a MAX chat and a Telegram destination."""

    id: str
    source_chat_id: str
    target_chat_id: int
    enabled: bool = True
    topic_binding_id: str | None = None
    created_at: datetime = Field(default_factory=utc_now)


class MessageMappingRecord(Record):
    """Persistent MAX-to-Telegram message mapping record.

    These records are central to replay safety, reply-chain preservation, and
    duplicate prevention after reconnects or repeated sync passes.
    """

    id: str
    max_chat_id: str
    max_message_id: str
    telegram_chat_id: int
    telegram_message_id: int
    message_thread_id: int | None = None
    direction: str = "max_to_telegram"
    created_at: datetime = Field(default_factory=utc_now)


class ArtifactRecord(Record):
    """Record describing an exported artifact produced by the archive layer."""

    id: str
    kind: str
    path: str
    chat_id: str | None = None
    created_at: datetime = Field(default_factory=utc_now)
    metadata: dict[str, Any] = Field(default_factory=dict)


class AuditLogRecord(Record):
    """Audit event for privileged or operational actions."""

    id: str
    actor: str | None = None
    action: str
    target: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utc_now)


class CommandHistoryRecord(Record):
    """Telegram or CLI command execution record."""

    id: str
    source: str
    actor: str | None = None
    command: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    status: str = "accepted"
    created_at: datetime = Field(default_factory=utc_now)
