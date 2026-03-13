"""Basic MAXBRIDGE client example.

This example exercises the stable high-level client against the experimental
mock MAX adapter.
"""

from __future__ import annotations

import asyncio

from maxbridge import MaxBridgeClient


async def main() -> None:
    """List chats and replay a few seeded updates."""

    async with MaxBridgeClient.from_config("config.toml") as client:
        chats = await client.get_chats()
        for chat in chats:
            print(chat.id, chat.title)

        async for event in client.iter_events(limit=10):
            print(event.type.value, event.chat_id)


if __name__ == "__main__":
    asyncio.run(main())
