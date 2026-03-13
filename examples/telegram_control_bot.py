"""Run the Telegram control bot.

This example starts the stable owner-only control plane around the local client
runtime and bridge manager.
"""

from __future__ import annotations

import asyncio

from maxbridge.bridge.manager import BridgeManager
from maxbridge.core.client import MaxBridgeClient
from maxbridge.telegram.bot import TelegramControlBot
from maxbridge.telegram.control_plane import ControlPlaneService
from maxbridge.telegram.forum import TelegramForumGateway


async def main() -> None:
    """Build the Telegram control-plane runtime and start polling."""

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
        control_plane = ControlPlaneService(client=client, bridge_manager=manager)
        bot = TelegramControlBot(config=client.config, control_plane=control_plane)
        await bot.run()


if __name__ == "__main__":
    asyncio.run(main())
