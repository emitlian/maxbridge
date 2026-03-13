"""Typed runtime configuration models.

This module defines the stable configuration contract for MAXBRIDGE.
Each section is deliberately narrow so that stable local-first behavior can
remain consistent even when the experimental MAX adapter changes.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, SecretStr


class ConfigSection(BaseModel):
    """Base class for configuration sections.

    Strict validation is enabled so that invalid keys fail fast during startup.
    That behavior is important for bridge tooling because silent typos in
    routing, storage, or owner access settings would be difficult to debug.
    """

    model_config = ConfigDict(extra="forbid", validate_assignment=True)


class CoreConfig(ConfigSection):
    """Settings for the stable client runtime.

    These values control local session naming, polling cadence, and logging.
    They are independent from any specific MAX transport implementation.
    """

    app_name: str = "MAXBRIDGE"
    session_name: str = "default"
    timezone: str = "UTC"
    poll_interval_seconds: int = 15
    max_batch_size: int = 100
    log_level: str = "INFO"
    json_logs: bool = False


class StorageConfig(ConfigSection):
    """Settings for the stable SQLite persistence layer.

    SQLite is the MVP backing store for sessions, chat state, bridge bindings,
    topic mappings, dedupe keys, archive artifacts, and audit records.
    """

    database_path: str = "./var/maxbridge.db"
    wal_mode: bool = True
    sqlite_busy_timeout_ms: int = 5_000


class TelegramConfig(ConfigSection):
    """Settings for the Telegram bridge and owner-only control plane.

    Telegram remains part of the stable core because the Bot API is the main
    operational surface for mirroring, status inspection, and safe control.
    """

    enabled: bool = False
    bot_token: SecretStr | None = None
    owner_user_ids: list[int] = Field(default_factory=list)
    admin_chat_id: int | None = None
    default_forum_chat_id: int | None = None
    parse_mode: Literal["HTML", "MarkdownV2"] = "HTML"


class BridgeConfig(ConfigSection):
    """Settings for stable bridge behavior.

    The bridge layer mirrors chats into Telegram topics, stores bindings, and
    applies routing rules. Dry-run defaults keep the first-run experience safe.
    """

    enabled: bool = False
    dry_run: bool = True
    sync_mode: Literal["mirror", "archive-only"] = "mirror"
    selected_chat_ids: list[str] = Field(default_factory=list)
    excluded_chat_ids: list[str] = Field(default_factory=list)
    skip_system_messages: bool = True
    create_topics: bool = True
    sender_header_template: str = "<b>{author}</b> [{time}]"


class ArchiveConfig(ConfigSection):
    """Settings for stable archive and export outputs."""

    export_dir: str = "./exports"
    media_dir: str = "./exports/media"
    default_format: Literal["json", "sqlite"] = "json"


class SecurityConfig(ConfigSection):
    """Settings for local safety and operator trust boundaries."""

    require_owner_allowlist: bool = True
    redact_secrets: bool = True
    audit_log: bool = True


class ExperimentalConfig(ConfigSection):
    """Settings for experimental MAX-specific capabilities.

    This section intentionally collects knobs that may depend on upstream
    behavior outside the stable MAXBRIDGE core. Reviewers should read this
    section as adapter-specific and less mature than the bridge/runtime stack.
    """

    max_adapter: Literal["mock", "unsupported", "replay"] = "mock"
    replay_updates_path: str | None = None
    enable_typing_actions: bool = False
    enable_reactions: bool = True


class MaxBridgeConfig(ConfigSection):
    """Top-level runtime configuration object.

    The stable sections describe behavior that MAXBRIDGE owns directly.
    The ``experimental`` section is intentionally separated so that operators
    can see which parts of the system depend on incomplete MAX capabilities.
    """

    core: CoreConfig = Field(default_factory=CoreConfig)
    storage: StorageConfig = Field(default_factory=StorageConfig)
    telegram: TelegramConfig = Field(default_factory=TelegramConfig)
    bridge: BridgeConfig = Field(default_factory=BridgeConfig)
    archive: ArchiveConfig = Field(default_factory=ArchiveConfig)
    security: SecurityConfig = Field(default_factory=SecurityConfig)
    experimental: ExperimentalConfig = Field(default_factory=ExperimentalConfig)
    config_source: str | None = None

    def redacted_dump(self) -> dict[str, Any]:
        """Return a config dump with secret values masked.

        This method is used for diagnostics and should never expose raw bot
        tokens or other future secret values in logs or operator output.
        """

        data = self.model_dump(mode="json")
        telegram_data = data.get("telegram", {})
        if telegram_data.get("bot_token") is not None:
            telegram_data["bot_token"] = "***"
        return data
