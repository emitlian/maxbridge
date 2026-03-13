"""Archive schema models.

The archive format is part of the stable core because it is how MAXBRIDGE
delivers portable exports and replayable fixtures independently from live MAX
transport capabilities.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from maxbridge.core.models import Chat, Message, User
from maxbridge.utils.time import utc_now

EXPORT_SCHEMA_VERSION = "1.0.0"


class ArchiveModel(BaseModel):
    """Base class for versioned archive payloads."""

    model_config = ConfigDict(extra="forbid")


class ChatArchive(ArchiveModel):
    """Versioned export payload for one chat and its known local context."""

    schema_version: str = EXPORT_SCHEMA_VERSION
    exported_at: datetime = Field(default_factory=utc_now)
    chat: Chat
    users: list[User] = Field(default_factory=list)
    messages: list[Message] = Field(default_factory=list)


class ArchiveManifest(ArchiveModel):
    """Top-level summary for a batch export run."""

    schema_version: str = EXPORT_SCHEMA_VERSION
    exported_at: datetime = Field(default_factory=utc_now)
    chat_count: int
    message_count: int
    artifact_paths: list[str] = Field(default_factory=list)
