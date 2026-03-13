"""Bridge CLI commands.

These commands cover the stable bridge operations that make the main vertical
slice reviewable from the command line.
"""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from maxbridge.bridge.manager import BridgeManager
from maxbridge.core.client import MaxBridgeClient
from maxbridge.telegram.forum import TelegramForumGateway

app = typer.Typer(help="Bridge commands")
console = Console()


@app.command("start")
def start_bridge(
    config: Path = typer.Option(Path("config.toml"), "--config"),
    once: bool = typer.Option(True, "--once/--follow"),
) -> None:
    """Run one bridge cycle or follow forever."""

    async def _run() -> None:
        """Construct the stable bridge runtime for one CLI execution."""

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
            if once:
                mirrored = await manager.sync_once()
                console.print(f"Mirrored {mirrored} message(s)")
            else:
                await manager.run_forever()

    import asyncio

    asyncio.run(_run())


@app.command("status")
def bridge_status(
    config: Path = typer.Option(Path("config.toml"), "--config"),
) -> None:
    """Print current bridge status."""

    async def _run() -> None:
        """Load bridge status from the stable runtime."""

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
            status = await manager.status()
            table = Table(title="Bridge Status")
            table.add_column("Key")
            table.add_column("Value")
            for key, value in status.items():
                table.add_row(key, str(value))
            console.print(table)

    import asyncio

    asyncio.run(_run())


@app.command("mappings")
def bridge_mappings(
    chat_id: str | None = typer.Option(None, "--chat"),
    limit: int = typer.Option(50, "--limit", min=1),
    config: Path = typer.Option(Path("config.toml"), "--config"),
) -> None:
    """Inspect stored MAX -> Telegram message mappings."""

    async def _run() -> None:
        """Read mapping rows from SQLite and render them for operators."""

        async with MaxBridgeClient.from_config(config) as client:
            mappings = await client.store.list_message_mappings(chat_id=chat_id, limit=limit)
            table = Table(title="Message Mappings")
            table.add_column("MAX Chat")
            table.add_column("MAX Message")
            table.add_column("Telegram Chat")
            table.add_column("Topic")
            table.add_column("Telegram Message")
            for mapping in mappings:
                table.add_row(
                    mapping.max_chat_id,
                    mapping.max_message_id,
                    str(mapping.telegram_chat_id),
                    str(mapping.message_thread_id),
                    str(mapping.telegram_message_id),
                )
            console.print(table)

    import asyncio

    asyncio.run(_run())


@app.command("bind")
def bind_chat(
    max_chat_id: str = typer.Argument(...),
    telegram_chat_id: int = typer.Option(..., "--telegram-chat-id"),
    message_thread_id: int | None = typer.Option(None, "--thread-id"),
    topic_title: str | None = typer.Option(None, "--topic-title"),
    config: Path = typer.Option(Path("config.toml"), "--config"),
) -> None:
    """Bind a MAX chat to a Telegram forum topic."""

    async def _run() -> None:
        """Bind directly or create a topic first, depending on CLI options."""

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
            if message_thread_id is None:
                binding = await manager.auto_bind_chat(
                    max_chat_id=max_chat_id,
                    telegram_chat_id=telegram_chat_id,
                    topic_title=topic_title,
                )
                console.print(
                    "Created topic and bound "
                    f"{binding.max_chat_id} -> {binding.telegram_chat_id}:{binding.message_thread_id}"
                )
                return
            binding = await manager.bind_chat(
                max_chat_id=max_chat_id,
                telegram_chat_id=telegram_chat_id,
                message_thread_id=message_thread_id,
                topic_title=topic_title,
            )
            console.print(
                "Bound existing topic "
                f"{binding.max_chat_id} -> {binding.telegram_chat_id}:{binding.message_thread_id}"
            )

    import asyncio

    asyncio.run(_run())


@app.command("unbind")
def unbind_chat(
    max_chat_id: str = typer.Argument(...),
    config: Path = typer.Option(Path("config.toml"), "--config"),
) -> None:
    """Disable a topic binding."""

    async def _run() -> None:
        """Disable the selected binding in SQLite."""

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
            await manager.unbind_chat(max_chat_id)
            console.print(f"Unbound {max_chat_id}")

    import asyncio

    asyncio.run(_run())
