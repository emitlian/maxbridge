-- Stable local session metadata for one runtime profile.
CREATE TABLE IF NOT EXISTS sessions (
    session_id TEXT PRIMARY KEY,
    account_id TEXT,
    adapter TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    metadata_json TEXT NOT NULL
);

-- Cached user records for archive export and bridge formatting.
CREATE TABLE IF NOT EXISTS users (
    user_id TEXT PRIMARY KEY,
    username TEXT,
    display_name TEXT NOT NULL,
    is_bot INTEGER NOT NULL DEFAULT 0,
    raw_json TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

-- Cached chats visible to the active adapter.
CREATE TABLE IF NOT EXISTS chats (
    chat_id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    chat_type TEXT NOT NULL,
    is_archived INTEGER NOT NULL DEFAULT 0,
    last_message_at TEXT,
    raw_json TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

-- Cached normalized messages keyed by chat and message identity.
CREATE TABLE IF NOT EXISTS messages (
    chat_id TEXT NOT NULL,
    message_id TEXT NOT NULL,
    author_id TEXT,
    text TEXT NOT NULL,
    created_at TEXT NOT NULL,
    edited_at TEXT,
    reply_to_message_id TEXT,
    thread_id TEXT,
    is_system INTEGER NOT NULL DEFAULT 0,
    raw_json TEXT NOT NULL,
    PRIMARY KEY (chat_id, message_id)
);

-- Logical bridge bindings from MAX chats to Telegram chats.
CREATE TABLE IF NOT EXISTS bridge_bindings (
    binding_id TEXT PRIMARY KEY,
    source_chat_id TEXT NOT NULL,
    target_chat_id INTEGER NOT NULL,
    enabled INTEGER NOT NULL DEFAULT 1,
    topic_binding_id TEXT,
    created_at TEXT NOT NULL,
    raw_json TEXT NOT NULL,
    UNIQUE (source_chat_id, target_chat_id)
);

-- Concrete one MAX chat = one Telegram topic bindings.
CREATE TABLE IF NOT EXISTS topic_bindings (
    binding_id TEXT PRIMARY KEY,
    max_chat_id TEXT NOT NULL UNIQUE,
    telegram_chat_id INTEGER NOT NULL,
    message_thread_id INTEGER NOT NULL,
    topic_title TEXT NOT NULL,
    enabled INTEGER NOT NULL DEFAULT 1,
    last_synced_at TEXT,
    created_at TEXT NOT NULL,
    raw_json TEXT NOT NULL
);

-- Persistent MAX-to-Telegram message ID mappings.
CREATE TABLE IF NOT EXISTS message_mappings (
    mapping_id TEXT PRIMARY KEY,
    max_chat_id TEXT NOT NULL,
    max_message_id TEXT NOT NULL,
    telegram_chat_id INTEGER NOT NULL,
    telegram_message_id INTEGER NOT NULL,
    message_thread_id INTEGER,
    direction TEXT NOT NULL,
    created_at TEXT NOT NULL,
    raw_json TEXT NOT NULL,
    UNIQUE (max_chat_id, max_message_id, telegram_chat_id, direction)
);

-- Generic stream cursors for replay, polling, or future adapters.
CREATE TABLE IF NOT EXISTS sync_cursors (
    stream_name TEXT PRIMARY KEY,
    cursor TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

-- Catalog of exported archive artifacts.
CREATE TABLE IF NOT EXISTS artifacts (
    artifact_id TEXT PRIMARY KEY,
    kind TEXT NOT NULL,
    path TEXT NOT NULL,
    chat_id TEXT,
    created_at TEXT NOT NULL,
    metadata_json TEXT NOT NULL,
    raw_json TEXT NOT NULL
);

-- Append-only audit trail for privileged actions.
CREATE TABLE IF NOT EXISTS audit_log (
    event_id TEXT PRIMARY KEY,
    actor TEXT,
    action TEXT NOT NULL,
    target TEXT,
    details_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    raw_json TEXT NOT NULL
);

-- History of accepted control-plane commands.
CREATE TABLE IF NOT EXISTS command_history (
    command_id TEXT PRIMARY KEY,
    source TEXT NOT NULL,
    actor TEXT,
    command TEXT NOT NULL,
    arguments_json TEXT NOT NULL,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL,
    raw_json TEXT NOT NULL
);

-- Persistent dedupe keys for idempotent bridge passes.
CREATE TABLE IF NOT EXISTS dedupe_hashes (
    dedupe_key TEXT PRIMARY KEY,
    scope TEXT NOT NULL,
    first_seen_at TEXT NOT NULL,
    metadata_json TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_messages_created_at ON messages (created_at);
CREATE INDEX IF NOT EXISTS idx_messages_author_id ON messages (author_id);
CREATE INDEX IF NOT EXISTS idx_audit_log_created_at ON audit_log (created_at);
CREATE INDEX IF NOT EXISTS idx_command_history_created_at ON command_history (created_at);
