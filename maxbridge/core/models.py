"""Typed domain models for MAXBRIDGE.

These models define the stable language shared by storage, archive, bridge,
Telegram, CLI, and tests. They intentionally describe portable concepts rather
than binding directly to any experimental MAX API surface.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from maxbridge.utils.time import utc_now


class Model(BaseModel):
    """Shared base model with strict defaults."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)


class ChatType(str, Enum):
    """Normalized chat categories used across the stable core."""

    DIRECT = "direct"
    GROUP = "group"
    CHANNEL = "channel"
    FORUM = "forum"
    UNKNOWN = "unknown"


class MediaKind(str, Enum):
    """Normalized media categories used by archive and bridge code."""

    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"
    DOCUMENT = "document"
    LINK = "link"
    OTHER = "other"


class PresenceState(str, Enum):
    """Normalized presence and typing states."""

    ONLINE = "online"
    OFFLINE = "offline"
    TYPING = "typing"
    IDLE = "idle"
    UNKNOWN = "unknown"


class EventType(str, Enum):
    """Normalized update types emitted by transports and replay fixtures."""

    MESSAGE_NEW = "message.new"
    MESSAGE_UPDATED = "message.updated"
    MESSAGE_DELETED = "message.deleted"
    REACTION = "reaction"
    PRESENCE = "presence"
    TYPING = "typing"


class Account(Model):
    """Account identity for the local MAX user."""

    id: str
    username: str | None = None
    display_name: str
    phone_number: str | None = None


class User(Model):
    """Normalized user profile."""

    id: str
    username: str | None = None
    display_name: str
    is_bot: bool = False


class Chat(Model):
    """Normalized chat or dialog metadata."""

    id: str
    title: str
    chat_type: ChatType = ChatType.UNKNOWN
    is_archived: bool = False
    last_message_at: datetime | None = None


class Media(Model):
    """Normalized media attachment metadata."""

    id: str
    kind: MediaKind = MediaKind.OTHER
    file_name: str | None = None
    mime_type: str | None = None
    size_bytes: int | None = None
    remote_url: str | None = None


class Reaction(Model):
    """Normalized reaction summary."""

    emoji: str
    count: int = 1
    reacted_by_me: bool = False


class TypingStatus(Model):
    """Typing or presence state for one user within one chat."""

    chat_id: str
    user_id: str
    state: PresenceState = PresenceState.TYPING
    expires_at: datetime | None = None


class Message(Model):
    """Normalized message payload.

    ``metadata`` is intentionally unstructured so adapters can preserve extra
    fields without forcing the stable core to change its public schema.
    """

    id: str
    chat_id: str
    author_id: str | None = None
    text: str = ""
    created_at: datetime = Field(default_factory=utc_now)
    edited_at: datetime | None = None
    reply_to_message_id: str | None = None
    thread_id: str | None = None
    media: list[Media] = Field(default_factory=list)
    reactions: list[Reaction] = Field(default_factory=list)
    is_system: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)


class Dialog(Model):
    """Chat plus currently known participants."""

    chat: Chat
    participants: list[User] = Field(default_factory=list)


class Session(Model):
    """Stable session metadata stored in SQLite."""

    id: str
    account_id: str | None = None
    adapter: str = "mock"
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ForwardRule(Model):
    """Routing rule placeholder for future richer sync policies."""

    name: str
    include_chat_ids: list[str] = Field(default_factory=list)
    exclude_chat_ids: list[str] = Field(default_factory=list)
    include_system_messages: bool = False


class MirrorBinding(Model):
    """Logical mapping between a MAX chat and a Telegram chat."""

    id: str
    source_chat_id: str
    target_chat_id: int
    enabled: bool = True
    topic_binding_id: str | None = None
    created_at: datetime = Field(default_factory=utc_now)


class TopicBinding(Model):
    """Concrete mapping from one MAX chat to one Telegram forum topic."""

    id: str
    max_chat_id: str
    telegram_chat_id: int
    message_thread_id: int
    topic_title: str
    enabled: bool = True
    last_synced_at: datetime | None = None
    created_at: datetime = Field(default_factory=utc_now)


class UpdateEvent(Model):
    """Normalized update emitted by a transport or replay source."""

    id: str
    type: EventType
    chat_id: str
    message: Message | None = None
    actor: User | None = None
    emitted_at: datetime = Field(default_factory=utc_now)
    cursor: str | None = None
    raw_payload: dict[str, Any] = Field(default_factory=dict)
