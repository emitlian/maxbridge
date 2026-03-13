from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from maxbridge.cli.main import app
from maxbridge.storage.sqlite import SQLiteStore

runner = CliRunner()


def test_cli_vertical_slice_end_to_end(tmp_path: Path) -> None:
    """The main demo path should work end-to-end through the CLI.

    The test covers the currently strongest vertical slice:
    init -> doctor -> list chats -> bind -> mirror -> inspect mappings.
    """

    config_path = tmp_path / "config.toml"

    result = runner.invoke(app, ["init", "--config", str(config_path)])
    assert result.exit_code == 0, result.output

    config_text = config_path.read_text(encoding="utf-8")
    config_text = config_text.replace("enabled = false", "enabled = true", 1)
    config_text = config_text.replace(
        "selected_chat_ids = []",
        'selected_chat_ids = ["chat_alpha"]',
        1,
    )
    config_path.write_text(config_text, encoding="utf-8")

    result = runner.invoke(app, ["doctor", "--config", str(config_path)])
    assert result.exit_code == 0, result.output
    assert "mock" in result.output

    result = runner.invoke(app, ["list-chats", "--config", str(config_path)])
    assert result.exit_code == 0, result.output
    assert "chat_alpha" in result.output

    result = runner.invoke(
        app,
        [
            "bridge",
            "bind",
            "chat_alpha",
            "--telegram-chat-id",
            "-1001234567890",
            "--topic-title",
            "Alpha Team",
            "--config",
            str(config_path),
        ],
    )
    assert result.exit_code == 0, result.output
    assert "Created topic and bound chat_alpha" in result.output

    result = runner.invoke(app, ["bridge", "start", "--config", str(config_path)])
    assert result.exit_code == 0, result.output
    assert "Mirrored 2 message(s)" in result.output

    result = runner.invoke(
        app,
        ["bridge", "mappings", "--chat", "chat_alpha", "--config", str(config_path)],
    )
    assert result.exit_code == 0, result.output
    assert "m001" in result.output
    assert "m002" in result.output

    store = SQLiteStore(tmp_path / "var" / "maxbridge.db")
    import asyncio

    async def _inspect() -> tuple[int, int]:
        await store.initialize()
        topic_binding = await store.get_topic_binding("chat_alpha")
        mappings = await store.list_message_mappings(chat_id="chat_alpha", limit=10)
        await store.close()
        return (
            1 if topic_binding is not None and topic_binding.enabled else 0,
            len(mappings),
        )

    binding_exists, mapping_count = asyncio.run(_inspect())
    assert binding_exists == 1
    assert mapping_count == 2
