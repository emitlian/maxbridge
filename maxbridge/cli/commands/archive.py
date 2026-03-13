"""Archive CLI commands.

Archive commands expose stable local-first capabilities that remain useful even
when the experimental MAX adapter is unavailable.
"""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from maxbridge.archive.exporter import ArchiveExporter
from maxbridge.core.client import MaxBridgeClient

app = typer.Typer(help="Archive commands")
console = Console()


@app.command("export")
def export_archive(
    chat_id: str | None = typer.Option(None, "--chat"),
    config: Path = typer.Option(Path("config.toml"), "--config"),
    sqlite_snapshot: bool = typer.Option(False, "--sqlite-snapshot"),
) -> None:
    """Export one chat or all known chats."""

    async def _run() -> None:
        """Populate the local index before running archive exports."""

        async with MaxBridgeClient.from_config(config) as client:
            await client.get_chats()
            for chat in await client.get_chats():
                await client.get_history(chat.id, limit=client.config.core.max_batch_size)
            exporter = ArchiveExporter(client.store, client.config.archive.export_dir)
            if chat_id:
                path = await exporter.export_chat_json(chat_id)
                console.print(f"Exported chat archive to [bold]{path}[/bold]")
            else:
                paths = await exporter.export_all_json()
                console.print(f"Exported {len(paths)} chat archive(s)")
            if sqlite_snapshot:
                snapshot = await exporter.export_sqlite_snapshot()
                console.print(f"SQLite snapshot: [bold]{snapshot}[/bold]")

    import asyncio

    asyncio.run(_run())


@app.command("stats")
def archive_stats(
    config: Path = typer.Option(Path("config.toml"), "--config"),
) -> None:
    """Show local storage stats."""

    async def _run() -> None:
        """Render archive-related SQLite counts."""

        async with MaxBridgeClient.from_config(config) as client:
            stats = await client.store.get_stats()
            table = Table(title="Archive Stats")
            table.add_column("Table")
            table.add_column("Count")
            for key, value in stats.items():
                table.add_row(key, str(value))
            console.print(table)

    import asyncio

    asyncio.run(_run())


@app.command("inspect-chat")
def inspect_chat(
    chat_id: str = typer.Argument(...),
    config: Path = typer.Option(Path("config.toml"), "--config"),
) -> None:
    """Inspect locally indexed messages for one chat."""

    async def _run() -> None:
        """Read message rows from SQLite and print a compact preview."""

        async with MaxBridgeClient.from_config(config) as client:
            messages = await client.store.get_messages(chat_id, limit=50)
            table = Table(title=f"Chat {chat_id}")
            table.add_column("Message ID")
            table.add_column("Author")
            table.add_column("Text")
            for message in messages:
                table.add_row(message.id, message.author_id or "-", message.text[:80])
            console.print(table)

    import asyncio

    asyncio.run(_run())
