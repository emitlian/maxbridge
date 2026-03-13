"""Binding helpers for bridge records.

These helpers keep bridge ID generation consistent across CLI flows, bot flows,
and automatic topic creation. Stable IDs matter because bindings are persisted
locally and reused after restarts.
"""

from __future__ import annotations

from maxbridge.core.models import MirrorBinding, TopicBinding
from maxbridge.storage.models import BridgeBindingRecord
from maxbridge.utils.ids import stable_id


def build_topic_binding(
    *,
    max_chat_id: str,
    telegram_chat_id: int,
    message_thread_id: int,
    topic_title: str,
) -> TopicBinding:
    """Create a stable topic binding model for one MAX chat."""

    return TopicBinding(
        id=stable_id("topic", max_chat_id, telegram_chat_id, message_thread_id),
        max_chat_id=max_chat_id,
        telegram_chat_id=telegram_chat_id,
        message_thread_id=message_thread_id,
        topic_title=topic_title,
    )


def build_bridge_binding(*, topic_binding: TopicBinding) -> BridgeBindingRecord:
    """Create the higher-level bridge binding record from a topic binding."""

    binding = MirrorBinding(
        id=stable_id("bridge", topic_binding.max_chat_id, topic_binding.telegram_chat_id),
        source_chat_id=topic_binding.max_chat_id,
        target_chat_id=topic_binding.telegram_chat_id,
        topic_binding_id=topic_binding.id,
    )
    return BridgeBindingRecord.model_validate(binding.model_dump(mode="json"))
