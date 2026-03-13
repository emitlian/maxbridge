"""Formatting MAX messages for Telegram topics.

Formatting lives in the stable bridge layer because it defines how MAX content
is represented inside Telegram forum topics, independent from the MAX adapter.
"""

from __future__ import annotations

from html import escape

from maxbridge.config.models import BridgeConfig
from maxbridge.core.models import Chat, Message, User


class TelegramMirrorFormatter:
    """Render MAX messages into Telegram-safe text.

    The formatter preserves a few core pieces of context:
    - author identity
    - event timestamp
    - lightweight reply hints when a direct Telegram reply is not available
    """

    def __init__(self, config: BridgeConfig) -> None:
        self._config = config

    def format(self, *, chat: Chat, message: Message, author: User | None) -> str:
        """Return an HTML-safe Telegram message body."""

        author_name = author.display_name if author is not None else "Unknown"
        header = self._config.sender_header_template.format(
            author=escape(author_name),
            time=message.created_at.isoformat(),
            chat=escape(chat.title),
        )
        body = escape(message.text or "")
        if message.reply_to_message_id:
            # A textual reply hint is kept even when a Telegram reply mapping
            # also exists, so exported or copied text remains understandable.
            body = f"<i>reply_to={escape(message.reply_to_message_id)}</i>\n{body}"
        return f"{header}\n{body}".strip()
