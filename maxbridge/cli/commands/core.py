"""Core CLI commands.

These commands cover the stable setup and inspection path:
- generate config
- inspect runtime state
- exercise the active MAX adapter by listing chats
"""

from __future__ import annotations

import platform
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from maxbridge.config import load_config, render_default_config
from maxbridge.core.client import MaxBridgeClient

app = typer.Typer(help="Core MAXBRIDGE commands")
console = Console()


@app.command("init")
def init_config(
    config: Path = typer.Option(Path("config.toml"), "--config"),
    force: bool = typer.Option(False, "--force", help="Overwrite an existing config file."),
) -> None:
    """Write a starter config file."""

    if config.exists() and not force:
        raise typer.BadParameter(f"Config already exists: {config}")
    config.parent.mkdir(parents=True, exist_ok=True)
    config.write_text(render_default_config(), encoding="utf-8")
    console.print(f"Wrote starter config to [bold]{config}[/bold]")


@app.command("doctor")
def doctor(
    config: Path = typer.Option(Path("config.toml"), "--config"),
) -> None:
    """Inspect runtime configuration and environment.

    The output explicitly calls out that the MAX adapter boundary is
    experimental so users and reviewers can distinguish mature and evolving
    parts of the repository.
    """

    loaded = load_config(config)
    table = Table(title="MAXBRIDGE Doctor")
    table.add_column("Check")
    table.add_column("Value")
    table.add_row("Python", platform.python_version())
    table.add_row("Config", loaded.config_source or "<env only>")
    table.add_row("Adapter", loaded.experimental.max_adapter)
    table.add_row("Adapter Boundary", "experimental")
    table.add_row("DB Path", loaded.storage.database_path)
    table.add_row("Bridge Enabled", str(loaded.bridge.enabled))
    table.add_row("Bridge Dry Run", str(loaded.bridge.dry_run))
    table.add_row("Telegram Enabled", str(loaded.telegram.enabled))
    table.add_row("Owner IDs", ",".join(str(user_id) for user_id in loaded.telegram.owner_user_ids) or "<empty>")
    console.print(table)


@app.command("list-chats")
def list_chats(
    config: Path = typer.Option(Path("config.toml"), "--config"),
) -> None:
    """List chats from the current transport."""

    async def _run() -> None:
        """Run the async chat listing flow inside the synchronous CLI command."""

        async with MaxBridgeClient.from_config(config) as client:
            chats = await client.get_chats()
            table = Table(title="Chats")
            table.add_column("ID")
            table.add_column("Title")
            table.add_column("Type")
            for chat in chats:
                table.add_row(chat.id, chat.title, chat.chat_type.value)
            console.print(table)

    import asyncio

    asyncio.run(_run())
