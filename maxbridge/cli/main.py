"""Typer application entry point.

The CLI is part of the stable operator surface. It intentionally groups bridge,
archive, Telegram, and core runtime commands behind a single local-first tool.
"""

from __future__ import annotations

import typer

from maxbridge.cli.commands.archive import app as archive_app
from maxbridge.cli.commands.bridge import app as bridge_app
from maxbridge.cli.commands.core import app as core_app
from maxbridge.cli.commands.telegram import app as telegram_app

app = typer.Typer(no_args_is_help=True, help="MAXBRIDGE CLI")
app.add_typer(core_app)
app.add_typer(archive_app, name="archive")
app.add_typer(bridge_app, name="bridge")
app.add_typer(telegram_app, name="telegram")


def run() -> None:
    """Run the root Typer application."""

    app()
