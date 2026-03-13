"""Formatting helpers for Telegram control-plane responses.

These helpers keep bot responses consistent and easy to scan without mixing
presentation concerns into the control-plane service itself.
"""

from __future__ import annotations

from maxbridge.core.models import Chat, TopicBinding


def render_chat_list(chats: list[Chat]) -> str:
    """Render a chat list for Telegram bot output."""

    if not chats:
        return "No chats available."
    return "\n".join(f"- {chat.title} (`{chat.id}`)" for chat in chats)


def render_bindings(bindings: list[TopicBinding]) -> str:
    """Render topic bindings for Telegram bot output."""

    if not bindings:
        return "No topic bindings configured."
    return "\n".join(
        f"- `{binding.max_chat_id}` -> chat `{binding.telegram_chat_id}` thread `{binding.message_thread_id}`"
        for binding in bindings
        if binding.enabled
    )


def render_status(status: dict[str, object]) -> str:
    """Render a small status dictionary for Telegram bot output."""

    return "\n".join(f"- {key}: {value}" for key, value in status.items())
