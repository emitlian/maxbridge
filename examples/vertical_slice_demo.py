"""Programmatic dry-run vertical slice for MAXBRIDGE.

This example demonstrates the strongest current demo path:
- mock MAX adapter
- one MAX chat to one Telegram topic
- dry-run mirroring
- SQLite message mappings
"""

from __future__ import annotations

import asyncio

from maxbridge.bridge.manager import BridgeManager
from maxbridge.core.client import MaxBridgeClient
from maxbridge.telegram.forum import TelegramForumGateway


async def main() -> None:
    """Bind one chat, run one sync pass, and print stored mappings."""

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
        await manager.auto_bind_chat(
            max_chat_id="chat_alpha",
            telegram_chat_id=client.config.telegram.default_forum_chat_id or -1001234567890,
            topic_title="Alpha Team",
        )
        mirrored = await manager.sync_once()
        mappings = await client.store.list_message_mappings(chat_id="chat_alpha", limit=10)
        print(f"mirrored={mirrored}")
        for mapping in mappings:
            print(
                mapping.max_chat_id,
                mapping.max_message_id,
                mapping.telegram_chat_id,
                mapping.message_thread_id,
                mapping.telegram_message_id,
            )


if __name__ == "__main__":
    asyncio.run(main())
