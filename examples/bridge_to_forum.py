"""Bridge MAX chats into Telegram forum topics in dry-run mode.

This example demonstrates the stable bridge runtime without requiring a live
Telegram bot token or a real MAX adapter.
"""

from __future__ import annotations

import asyncio

from maxbridge.bridge.manager import BridgeManager
from maxbridge.core.client import MaxBridgeClient
from maxbridge.telegram.forum import TelegramForumGateway


async def main() -> None:
    """Run one dry-run bridge pass and print the mirrored count."""

    async with MaxBridgeClient.from_config("config.toml") as client:
        gateway = TelegramForumGateway(
            client.config.telegram.bot_token.get_secret_value()
            if client.config.telegram.bot_token
            else None,
            default_forum_chat_id=client.config.telegram.default_forum_chat_id,
            parse_mode=client.config.telegram.parse_mode,
            dry_run=client.config.bridge.dry_run,
        )
        manager = BridgeManager(client, gateway)
        mirrored = await manager.sync_once()
        print(f"Mirrored {mirrored} message(s)")


if __name__ == "__main__":
    asyncio.run(main())
