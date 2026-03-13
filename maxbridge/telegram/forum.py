"""Telegram forum gateway for topic creation and message delivery.

Telegram support is part of the stable MAXBRIDGE core. The gateway isolates
Bot API calls so bridge logic can stay transport-agnostic and test-friendly.
"""

from __future__ import annotations

from typing import Any

from maxbridge.core.exceptions import BridgeBindingError
from maxbridge.utils.ids import stable_digest
from maxbridge.utils.logging import get_logger

logger = get_logger(__name__)

try:  # pragma: no cover - exercised in integration environments
    from telegram import Bot
except ImportError:  # pragma: no cover
    Bot = Any


class TelegramForumGateway:
    """Wrapper around Telegram Bot API for forum-topic mirroring.

    Dry-run mode is a first-class feature because it makes the bridge demo path
    safe and reviewable without needing a live Telegram bot during development.
    """

    def __init__(
        self,
        token: str | None,
        *,
        default_forum_chat_id: int | None = None,
        parse_mode: str = "HTML",
        dry_run: bool = True,
    ) -> None:
        """Create a Telegram gateway for bridge operations."""

        self.token = token
        self.default_forum_chat_id = default_forum_chat_id
        self.parse_mode = parse_mode
        self.dry_run = dry_run
        self._bot = Bot(token=token) if token and Bot is not Any else None

    async def create_topic(self, chat_id: int, title: str) -> int:
        """Create a forum topic or return a deterministic dry-run ID."""

        if self.dry_run:
            logger.info("Dry-run: create topic %s in Telegram chat %s", title, chat_id)
            return int(stable_digest("topic", chat_id, title)[:8], 16)
        if self._bot is None:
            raise BridgeBindingError("Telegram bot token is required to create forum topics.")
        topic = await self._bot.create_forum_topic(chat_id=chat_id, name=title)
        return int(topic.message_thread_id)

    async def send_message(
        self,
        chat_id: int,
        thread_id: int,
        text: str,
        *,
        reply_to_message_id: int | None = None,
    ) -> int:
        """Send one mirrored message into a Telegram forum topic.

        ``reply_to_message_id`` is optional and is used when the bridge already
        knows the Telegram message ID of the parent MAX message.
        """

        if self.dry_run:
            logger.info(
                "Dry-run: send Telegram message to chat=%s thread=%s reply_to=%s text=%s",
                chat_id,
                thread_id,
                reply_to_message_id,
                text[:120],
            )
            return int(
                stable_digest("message", chat_id, thread_id, reply_to_message_id or 0, text)[:8],
                16,
            )
        if self._bot is None:
            raise BridgeBindingError("Telegram bot token is required to send forum messages.")
        message = await self._bot.send_message(
            chat_id=chat_id,
            text=text,
            message_thread_id=thread_id,
            reply_to_message_id=reply_to_message_id,
            parse_mode=self.parse_mode,
            disable_web_page_preview=True,
        )
        return int(message.message_id)

    async def close(self) -> None:
        """Close gateway resources when future implementations require it."""

        return None
