# Demo Storyboard

This is the recommended 20 to 40 second demo path for MAXBRIDGE submission material.

Goal:

- show one clean vertical slice
- make the local-first bridge model obvious
- show that bindings and mappings are persisted
- show the stable core and experimental mock adapter boundary without over-explaining it

Suggested sequence:

1. Run `maxbridge init --config config.toml`
2. Run `maxbridge doctor --config config.toml`
3. Open `config.toml` briefly and show:
   - `experimental.max_adapter = "mock"`
   - bridge dry-run enabled
   - Telegram forum target configured
4. Run `maxbridge bridge bind chat_alpha --telegram-chat-id -1001234567890 --topic-title "Alpha Team" --config config.toml`
5. Run `maxbridge bridge start --config config.toml`
6. Run `maxbridge bridge mappings --chat chat_alpha --config config.toml`

What to emphasize on screen:

- the mock MAX adapter is explicit
- one MAX chat maps to one Telegram topic
- the topic is created or reused
- the mirrored message includes author context
- the reply chain is preserved when the parent mapping already exists
- SQLite-backed message mappings can be inspected immediately after the sync pass

Suggested captions:

- "Initialize local-first runtime"
- "Inspect stable core and experimental adapter boundary"
- "Bind one MAX chat to one Telegram topic"
- "Mirror messages into Telegram forum topic"
- "Inspect SQLite-backed message mappings"

Suggested close:

"Local-first bridge, archive, and control-plane tooling with an explicit experimental MAX adapter boundary."
