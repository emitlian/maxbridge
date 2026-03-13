"""Async event bus helpers.

The event bus is intentionally lightweight. It provides a stable internal hook
point without introducing a heavier dependency for a small local-first project.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from maxbridge.core.models import UpdateEvent

EventHandler = Callable[[UpdateEvent], Awaitable[None]]


class EventBus:
    """Simple in-process async event dispatcher."""

    def __init__(self) -> None:
        """Initialize an empty handler registry."""

        self._handlers: list[EventHandler] = []

    def register(self, handler: EventHandler) -> EventHandler:
        """Register a new async handler."""

        self._handlers.append(handler)
        return handler

    def unregister(self, handler: EventHandler) -> None:
        """Remove a previously registered handler."""

        self._handlers = [item for item in self._handlers if item is not handler]

    async def emit(self, event: UpdateEvent) -> None:
        """Deliver one event to all registered handlers in registration order."""

        for handler in tuple(self._handlers):
            await handler(event)
