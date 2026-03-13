"""Configuration loader with TOML/YAML file support and env overrides.

The configuration layer is part of the stable MAXBRIDGE core. It resolves file
paths relative to the config file, applies environment overrides, and validates
the final structure before any bridge or Telegram logic starts.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from maxbridge.config.models import MaxBridgeConfig
from maxbridge.core.exceptions import ConfigError


def load_config(path: str | Path | None = None, *, env_prefix: str = "MAXBRIDGE") -> MaxBridgeConfig:
    """Load configuration from file and environment variables.

    Environment variables always win over file values. That priority allows
    local secrets and deployment-specific overrides without mutating the base
    config on disk.
    """

    raw: dict[str, Any] = {}
    source: str | None = None

    if path is not None:
        config_path = Path(path)
        if not config_path.exists():
            raise ConfigError(f"Config file not found: {config_path}")
        raw = _load_file(config_path)
        # Relative paths in config files should follow the config file location,
        # not the current working directory of the CLI process.
        raw = _resolve_relative_paths(raw, base_dir=config_path.parent)
        source = str(config_path)

    env_data = _load_env_overrides(env_prefix)
    merged = _merge_dicts(raw, env_data)
    config = MaxBridgeConfig.model_validate(merged)
    return config.model_copy(update={"config_source": source})


def render_default_config() -> str:
    """Render a starter TOML config file.

    The generated template is intentionally conservative:
    - bridge operations start disabled
    - dry-run is enabled
    - the mock adapter is selected
    - Telegram forum IDs remain commented placeholders
    """

    return """[core]
app_name = "MAXBRIDGE"
session_name = "default"
timezone = "UTC"
poll_interval_seconds = 15
max_batch_size = 100
log_level = "INFO"
json_logs = false

[storage]
database_path = "./var/maxbridge.db"
wal_mode = true
sqlite_busy_timeout_ms = 5000

[telegram]
enabled = false
bot_token = ""
owner_user_ids = []
# admin_chat_id = -1001234567890
# default_forum_chat_id = -1001234567890
parse_mode = "HTML"

[bridge]
enabled = false
dry_run = true
sync_mode = "mirror"
selected_chat_ids = []
excluded_chat_ids = []
skip_system_messages = true
create_topics = true
sender_header_template = "<b>{author}</b> [{time}]"

[archive]
export_dir = "./exports"
media_dir = "./exports/media"
default_format = "json"

[security]
require_owner_allowlist = true
redact_secrets = true
audit_log = true

[experimental]
max_adapter = "mock"
replay_updates_path = ""
enable_typing_actions = false
enable_reactions = true
"""


def _load_file(path: Path) -> dict[str, Any]:
    """Load a config file into a plain dictionary."""

    suffix = path.suffix.lower()
    if suffix == ".toml":
        import tomllib

        return tomllib.loads(path.read_text(encoding="utf-8"))
    if suffix in {".yaml", ".yml"}:
        try:
            import yaml
        except ImportError as exc:  # pragma: no cover
            raise ConfigError("PyYAML is required to load YAML config files") from exc
        loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
        return loaded if isinstance(loaded, dict) else {}
    raise ConfigError(f"Unsupported config format: {path.suffix}")


def _load_env_overrides(prefix: str) -> dict[str, Any]:
    """Collect nested env overrides using ``SECTION__KEY`` semantics."""

    data: dict[str, Any] = {}
    marker = f"{prefix}__"
    for key, value in os.environ.items():
        if not key.startswith(marker):
            continue
        path = key[len(marker) :].lower().split("__")
        _set_nested_value(data, path, _coerce_env_value(value))
    return data


def _coerce_env_value(value: str) -> Any:
    """Best-effort parse JSON-like env values before falling back to strings."""

    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return value


def _set_nested_value(target: dict[str, Any], path: list[str], value: Any) -> None:
    """Create nested dictionaries for env override assignment."""

    cursor = target
    for key in path[:-1]:
        child = cursor.get(key)
        if not isinstance(child, dict):
            child = {}
            cursor[key] = child
        cursor = child
    cursor[path[-1]] = value


def _merge_dicts(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Recursively merge dictionaries with override precedence."""

    merged: dict[str, Any] = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _merge_dicts(merged[key], value)
        else:
            merged[key] = value
    return merged


def _resolve_relative_paths(raw: dict[str, Any], *, base_dir: Path) -> dict[str, Any]:
    """Resolve known path-like settings relative to the config file directory.

    Only a small, explicit list of keys is resolved. That keeps the behavior
    predictable and avoids surprising transformations of arbitrary string data.
    """

    resolved = _merge_dicts({}, raw)

    def _resolve(section: str, key: str) -> None:
        """Resolve one ``section.key`` pair in-place when it contains a path."""

        section_data = resolved.get(section)
        if not isinstance(section_data, dict):
            return
        value = section_data.get(key)
        if not isinstance(value, str) or not value:
            return
        candidate = Path(value)
        if candidate.is_absolute():
            return
        section_data[key] = str((base_dir / candidate).resolve())

    _resolve("storage", "database_path")
    _resolve("archive", "export_dir")
    _resolve("archive", "media_dir")
    _resolve("experimental", "replay_updates_path")
    return resolved
