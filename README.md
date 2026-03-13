# MAXBRIDGE

[![CI](https://github.com/emitlian/maxbridge/actions/workflows/ci.yml/badge.svg)](https://github.com/emitlian/maxbridge/actions/workflows/ci.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/license-MIT-2ea44f.svg)](LICENSE)
[![Stability Model](https://img.shields.io/badge/stability-stable%20core%20%2B%20experimental%20adapter-0A66C2.svg)](#stability-model)

MAXBRIDGE is a local-first interoperability client and sync toolkit for MAX with Telegram forum mirroring, archive import/export, and an owner-only Telegram bot control plane.

Runtime baseline: Python 3.11+.
Verified locally on Python 3.11.

It is designed as foundational OSS infrastructure rather than a thin API wrapper:

- async-first Python SDK with typed models and clean client abstractions;
- archive/export pipeline for chat history, replay fixtures, and offline inspection;
- one MAX chat to one Telegram forum topic bridging model;
- owner-only Telegram control plane for status, bindings, sync, and safe personal automation;
- storage, routing, and replay layers that remain useful even when a safe public MAX user API is incomplete.

## Who It Is For

MAXBRIDGE is for developers, power users, archivists, and operators who want:

- a local-first way to index and inspect their own MAX chat history
- deterministic mirroring from MAX into Telegram forum topics
- SQLite-backed bridge state that survives restarts and reconnects
- a Telegram bot control plane for safe owner-only operations
- export and replay tooling that remains useful even before a full MAX user adapter exists

## Stability Model

Stable core:

- `maxbridge.config`
- `maxbridge.core` interfaces and typed models
- `maxbridge.storage`
- `maxbridge.archive`
- `maxbridge.bridge`
- `maxbridge.telegram`
- `maxbridge.cli`

Experimental MAX adapter layer:

- `maxbridge.experimental`
- `maxbridge.auth`

The stable core is intended to remain useful even if the real MAX user-layer adapter changes or is unavailable.
The experimental layer exists to keep MAX-specific login and transport concerns isolated from the local-first bridge, archive, and Telegram runtime.

## What Is Stable Today

The following areas are already treated as stable, production-minded repository foundations:

- config loading with TOML/YAML support and env overrides
- typed domain models
- SQLite persistence, migrations, audit history, dedupe keys, and bridge mappings
- archive export and import infrastructure
- bridge manager, topic binding model, dedupe, and routing
- Telegram forum gateway and owner-only control plane
- CLI, replay/export workflow, and the dry-run vertical slice

## What Is Experimental Today

The following areas are explicitly experimental:

- MAX transport adapters
- MAX auth/login flows
- any future integration that depends on incomplete or unstable upstream MAX capabilities

MAXBRIDGE is intentionally honest here. The repository does not pretend that unsupported MAX user-layer integration is stable.

## Positioning

MAXBRIDGE exists to reduce vendor lock-in and make migration, mirroring, and personal interoperability practical.

## Why This Matters For OSS

- reduces lock-in around chat history, routing state, and operational workflows
- enables migration, archival, and replay from a local SQLite-backed foundation
- gives developers a local-first bridge layer instead of another closed sync silo
- makes emerging messaging ecosystems easier to integrate with existing Telegram-centric workflows
- keeps bridge logic inspectable, scriptable, and testable for the broader Python ecosystem

It is explicitly **not**:

- a spam tool;
- a bulk messaging engine;
- a stealth automation client;
- a credential extractor;
- an exploit or ToS bypass framework.

When a safe public integration path for MAX is unavailable, MAXBRIDGE uses clean interfaces, mocks, replay fixtures, and experimental adapters rather than unsafe workarounds.

## Elevator Pitch

Think of MAXBRIDGE as a blend of Telethon-style DX, aiogram-style ergonomics, and a local-first archive/bridge runtime:

```python
from maxbridge import MaxBridgeClient


async def main() -> None:
    async with MaxBridgeClient.from_config("config.toml") as client:
        chats = await client.get_chats()
        for chat in chats:
            print(chat.title)

        async for event in client.iter_events():
            print(event.type, event.chat_id)
```

## Why Local-First Matters

MAXBRIDGE keeps sessions, chat indexes, bridge bindings, mappings, audit history, and archive artifacts on the user's machine by default.

That matters because it gives the project a clear trust model:

- no cloud dependency is required for the core workflow
- operators can inspect the SQLite state directly
- bridge recovery does not depend on a remote control service
- archive and replay tooling remain usable offline
- the project reduces lock-in instead of adding a new one

## Architecture

```text
        +--------------------+
        |   CLI / Bot UX     |
        | Typer + Telegram   |
        +---------+----------+
                  |
        +---------v----------+
        | Bridge Manager     |
        | Routing / Dedupe   |
        | Topic Bindings     |
        +---------+----------+
                  |
        +---------v----------+
        | Stable Core        |
        | Client / Storage   |
        | Archive / CLI      |
        +---------+----------+
                  |
     +------------+-------------+
     |                          |
+----v----+              +------v------+
| Storage  |              | Transports  |
| SQLite   |              | Mock / Exp. |
| Archive  |              | Adapters    |
+----+----+              +------+------+
     |                          |
     +-------------+------------+
                   |
            +------v----------------+
            | Experimental MAX      |
            | Adapter / Replay/Test |
            +-------------+
```

## Repository Layout

```text
maxbridge/
  pyproject.toml
  README.md
  LICENSE
  .env.example
  docker-compose.yml
  mkdocs.yml
  docs/
  examples/
  maxbridge/
    archive/
    auth/
    bridge/
    cli/
    config/
    core/
    experimental/
    max/
    storage/
    telegram/
    utils/
  tests/
    fixtures/
    integration/
    replay_cases/
    unit/
```

## MVP Scope

Phase 1 focuses on safe and shippable foundations:

- project scaffolding and packaging;
- typed models and client interfaces;
- local config loading with env overrides;
- SQLite storage with migrations;
- JSON archive export and SQLite snapshot export;
- Telegram forum gateway skeleton and bridge manager;
- owner-only Telegram control bot skeleton;
- mock transport and replay-oriented development path;
- tests, examples, docs, and CI-ready tooling metadata.

## Experimental Boundaries

The following are intentionally treated as experimental or stubbed:

- MAX login and transport integration when no safe public user API is available;
- reactions, typing, and bidirectional sync details that depend on adapter capabilities;
- importing data back into MAX or performing actions that would require bypassing protections.

Those areas are intentionally isolated in `maxbridge.experimental`, `maxbridge.auth`, and the abstract interface in `maxbridge.core.transport`.

## Quickstart

1. Create a virtual environment with Python 3.11+.
2. Install the package:

```bash
pip install -e ".[dev]"
```

3. Generate a starter config:

```bash
maxbridge init --config config.toml
```

4. Inspect the environment:

```bash
maxbridge doctor --config config.toml
```

5. List mock chats or chats from an installed adapter:

```bash
maxbridge list-chats --config config.toml
```

6. Run the Telegram control bot:

```bash
maxbridge telegram run-bot --config config.toml
```

## Issues And Contributions

MAXBRIDGE uses GitHub issue forms for the first round of triage and a lightweight contribution checklist for pull requests.

- use the issue template for reproducible bugs, bridge regressions, storage issues, or documentation gaps
- read [CONTRIBUTING.md](CONTRIBUTING.md) before opening a pull request
- keep the stable core and experimental adapter boundary explicit in code, docs, and tests
- avoid features that change the project into bulk messaging, hidden automation, or unauthorized account control

## Python Support

- baseline runtime: Python 3.11+
- local smoke and test runs in this repository were executed on Python 3.11
- CI is configured for Python 3.11

## Telegram Forum Mirroring

The core mapping model is:

```text
one MAX chat = one Telegram forum topic
```

Benefits:

- preserves isolation between conversations;
- makes replay and resync deterministic;
- keeps message-thread mapping manageable;
- creates a practical control plane for bridge operations.

## Telegram Control Plane

The Telegram bot is an owner-only control surface for the local runtime.

It is designed to let the account owner:

- inspect bridge and storage health
- list chats and bindings
- bind or unbind chats from Telegram topics
- trigger sync and archive export operations
- send a deliberate message, reaction, or typing state through the configured account

It is not designed as a public bot, marketing bot, or bulk outreach surface.

## Bridge Bindings And SQLite Mappings

Two SQLite-backed records are central to the bridge design:

- topic bindings: the concrete mapping from one MAX chat to one Telegram forum topic
- message mappings: the concrete mapping from one MAX message to one Telegram message

Why this matters:

- repeated sync passes can stay idempotent
- reply chains can be preserved when the parent MAX message already has a Telegram mapping
- bridge state survives restarts
- operators can inspect the local database or CLI outputs to understand exactly what happened

## Vertical Slice Demo

The main end-to-end demo path for MAXBRIDGE is:

```text
one MAX chat = one Telegram forum topic
new MAX message arrives
topic is created or reused
message is mirrored into the topic
author header is preserved
reply chain is preserved via Telegram reply mapping when available
SQLite stores topic bindings and MAX -> Telegram message mappings
```

This scenario already works with the experimental mock MAX adapter and Telegram dry-run mode.

### Demo commands

```bash
maxbridge init --config config.toml
maxbridge doctor --config config.toml
maxbridge list-chats --config config.toml
maxbridge bridge bind chat_alpha --telegram-chat-id -1001234567890 --topic-title "Alpha Team" --config config.toml
maxbridge bridge start --config config.toml
maxbridge bridge mappings --chat chat_alpha --config config.toml
```

What this demonstrates:

- `init` creates a runnable local-first config
- `doctor` confirms runtime, adapter, and storage settings
- `list-chats` exercises the experimental mock MAX adapter
- `bridge bind` creates or stores `one chat = one topic`
- `bridge start` mirrors messages through the Telegram gateway
- `bridge mappings` proves the SQLite mapping layer recorded the mirror operation

For README screenshots or a gif, this is the path to record.

## Security Notes

### Threat model

MAXBRIDGE assumes:

- the account owner explicitly authorizes local use;
- secrets stay on the local machine;
- Telegram control access is restricted to configured owner IDs;
- bridge actions are auditable and safe by default.

### What this project does not do

- no mass messaging;
- not a bulk messaging tool;
- no credential theft;
- not for unauthorized account access;
- no hidden auth flows;
- not for hidden automation;
- no remote telemetry by default;
- no bypass guidance for protected or private APIs.

### Safe defaults

- `dry_run = true` by default for bridge operations;
- no bridge actions without explicit config;
- owner-only Telegram command handling;
- secrets are represented with `SecretStr` and never logged intentionally.

### Ethics

MAXBRIDGE is intentionally scoped to personal interoperability, migration, sync, archive/export, and local-first control.

The repository does not target:

- bulk messaging
- unsolicited outreach
- spam automation
- hidden account control
- credential extraction
- bypassing protections or private APIs

Allowed operating model:

- owner-controlled, local-first interoperability only
- explicit configuration and local storage by the account owner
- bridge, archive, export, replay, and safe control-plane workflows

## Roadmap

### Phase 1: MVP foundation

- config, storage, typed models, client abstraction;
- archive export, replay tooling, mock transport;
- Telegram bridge and control-plane skeleton;
- docs, tests, and examples.

### Phase 2: Practical bridge

- stable topic creation and binding flows;
- retry/resume, cursors, replay catch-up;
- richer formatters and routing rules;
- reactions and typing abstraction improvements.

### Phase 3: Mature OSS tooling

- bidirectional architecture;
- plugin/adapters system;
- packaging and release automation;
- expanded fixtures, docs, and migration helpers.

## Contributing

Contributions are welcome, especially around:

- safe MAX adapters;
- archive schema evolution;
- replay fixtures and tests;
- Telegram UX and control-plane hardening;
- docs and examples.

Start with [CONTRIBUTING.md](CONTRIBUTING.md) and [docs/index.md](docs/index.md) for documentation entry points.
