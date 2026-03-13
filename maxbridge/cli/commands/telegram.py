"""Telegram control bot commands.

Telegram commands start the owner-only control plane and are part of the stable
operator workflow for the bridge runtime.
"""

from __future__ import annotations

from pathlib import Path

import typer

from maxbridge.bridge.manager import BridgeManager
from maxbridge.core.client import MaxBridgeClient
from maxbridge.telegram.bot import TelegramControlBot
from maxbridge.telegram.control_plane import ControlPlaneService
from maxbridge.telegram.forum import TelegramForumGateway

app = typer.Typer(help="Telegram control-plane commands")


@app.command("run-bot")
def run_bot(
    config: Path = typer.Option(Path("config.toml"), "--config"),
) -> None:
    """Run the owner-only Telegram bot."""

    async def _run() -> None:
        """Construct the Telegram control-plane runtime and start polling."""

        async with MaxBridgeClient.from_config(config) as client:
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

    import asyncio

    asyncio.run(_run())
