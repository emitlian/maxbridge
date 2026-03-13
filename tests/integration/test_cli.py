from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from maxbridge.cli.main import app

runner = CliRunner()


def test_cli_init_writes_config(tmp_path: Path) -> None:
    """The init command should create a starter config file."""

    config_path = tmp_path / "config.toml"
    result = runner.invoke(app, ["init", "--config", str(config_path)])

    assert result.exit_code == 0
    assert config_path.exists()
