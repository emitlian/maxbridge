"""Selective sync and routing policy.

Routing is part of the stable core because it defines local operator intent.
The policy is intentionally simple in the MVP so users can reason about which
chats will mirror without digging through hidden automation rules.
"""

from __future__ import annotations

from dataclasses import dataclass

from maxbridge.config.models import BridgeConfig


@dataclass(slots=True)
class RouteDecision:
    """Result of a routing policy evaluation."""

    allowed: bool
    reason: str


class RoutingPolicy:
    """Apply simple whitelist/blacklist logic for bridge flows."""

    def __init__(self, config: BridgeConfig) -> None:
        self._config = config

    def should_sync(self, chat_id: str, *, is_system: bool = False) -> RouteDecision:
        """Evaluate whether a chat or message should be mirrored.

        The decision includes a human-readable reason so CLI logs and future UI
        surfaces can explain why data was or was not routed.
        """

        if self._config.selected_chat_ids and chat_id not in self._config.selected_chat_ids:
            return RouteDecision(False, "chat not in selected_chat_ids")
        if chat_id in self._config.excluded_chat_ids:
            return RouteDecision(False, "chat in excluded_chat_ids")
        if is_system and self._config.skip_system_messages:
            return RouteDecision(False, "system messages are filtered")
        return RouteDecision(True, "allowed")
