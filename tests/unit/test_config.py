from __future__ import annotations

from pathlib import Path

from maxbridge.config import load_config, render_default_config


def test_load_config_with_env_override(monkeypatch, tmp_path: Path) -> None:
    """Environment overrides should win over file values and resolve paths."""

    config_path = tmp_path / "config.toml"
    config_path.write_text(render_default_config(), encoding="utf-8")

    monkeypatch.setenv("MAXBRIDGE__BRIDGE__ENABLED", "true")
    monkeypatch.setenv("MAXBRIDGE__TELEGRAM__OWNER_USER_IDS", "[1, 2]")

    config = load_config(config_path)

    assert config.bridge.enabled is True
    assert config.telegram.owner_user_ids == [1, 2]
    assert config.config_source == str(config_path)
    assert config.storage.database_path == str((tmp_path / "var" / "maxbridge.db").resolve())
