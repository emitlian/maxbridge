# Security

MAXBRIDGE is designed for local-first personal interoperability.

Security principles:

- no hidden remote sync;
- no telemetry by default;
- owner-only Telegram bot commands;
- secrets stored locally and loaded from environment;
- dry-run defaults for bridge flows;
- auditable command and bridge activity in local SQLite storage.

The project does not implement or endorse bypassing protections, credential extraction, or mass messaging.

Stable core and experimental boundary:

- stable core: config, storage, archive, bridge, Telegram control plane, CLI, and replay/export infrastructure
- experimental boundary: MAX auth and MAX transport adapters

This split is intentional. The repository keeps local-first bridge and archive behavior stable even when real MAX user-layer integration remains incomplete or changes upstream.
