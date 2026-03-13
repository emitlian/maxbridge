"""Telegram control-plane service.

The Telegram bot is intentionally owner-only and local-first. This service
contains the actual bridge and archive operations so command handlers remain
thin and audit logging stays centralized.
"""

from __future__ import annotations

import json

from maxbridge.archive.exporter import ArchiveExporter
from maxbridge.storage.models import AuditLogRecord, CommandHistoryRecord
from maxbridge.telegram.formatting import render_bindings, render_chat_list, render_status
from maxbridge.utils.ids import stable_id


class ControlPlaneService:
    """Application-facing operations exposed via the Telegram bot.

    Each public method corresponds to one safe operational capability such as:
    status checks, chat binding, archive export, or a deliberate message send on
    behalf of the local account owner.
    """

    def __init__(self, *, client, bridge_manager) -> None:
        """Initialize the owner control plane around a client runtime."""

        self.client = client
        self.bridge_manager = bridge_manager
        self.exporter = ArchiveExporter(client.store, client.config.archive.export_dir)

    async def status_text(self, *, actor: str | None = None) -> str:
        """Return bridge status text and audit the request."""

        status = await self.bridge_manager.status()
        await self._record_command("status", {}, actor=actor)
        return render_status(status)

    async def health_text(self, *, actor: str | None = None) -> str:
        """Return SQLite table counts and audit the request."""

        stats = await self.client.store.get_stats()
        await self._record_command("health", {}, actor=actor)
        return render_status(stats)

    async def login_status_text(self, *, actor: str | None = None) -> str:
        """Return the current session state for diagnostics."""

        session = self.client.session
        await self._record_command("login_status", {}, actor=actor)
        if session is None:
            return "No session initialized."
        return f"adapter={session.adapter}\nsession_id=`{session.id}`\naccount_id=`{session.account_id}`"

    async def list_chats_text(self, *, actor: str | None = None) -> str:
        """List chats visible to the current MAX adapter."""

        chats = await self.client.get_chats()
        await self._record_command("list_chats", {}, actor=actor)
        return render_chat_list(chats)

    async def bindings_text(self, *, actor: str | None = None) -> str:
        """List current topic bindings."""

        bindings = await self.client.store.list_topic_bindings()
        await self._record_command("bindings", {}, actor=actor)
        return render_bindings(bindings)

    async def sync_now(self, *, actor: str | None = None) -> str:
        """Run one explicit bridge pass on demand."""

        mirrored = await self.bridge_manager.sync_once()
        await self._record_command("sync_now", {}, actor=actor)
        return f"Mirrored {mirrored} message(s)."

    async def pause(self, *, actor: str | None = None) -> str:
        """Pause the bridge and record the action."""

        self.bridge_manager.pause()
        await self._record_command("pause", {}, actor=actor)
        return "Bridge paused."

    async def resume(self, *, actor: str | None = None) -> str:
        """Resume the bridge and record the action."""

        self.bridge_manager.resume()
        await self._record_command("resume", {}, actor=actor)
        return "Bridge resumed."

    async def bind_chat(
        self,
        max_chat_id: str,
        telegram_chat_id: int,
        message_thread_id: int | None = None,
        topic_title: str | None = None,
        *,
        actor: str | None = None,
    ) -> str:
        """Bind a MAX chat to a Telegram forum topic.

        When ``message_thread_id`` is omitted, the Telegram gateway is asked to
        create a new topic first. This keeps the "one MAX chat = one Telegram
        forum topic" model consistent across CLI and bot flows.
        """

        if message_thread_id is None:
            binding = await self.bridge_manager.auto_bind_chat(
                max_chat_id=max_chat_id,
                telegram_chat_id=telegram_chat_id,
                topic_title=topic_title,
            )
        else:
            binding = await self.bridge_manager.bind_chat(
                max_chat_id=max_chat_id,
                telegram_chat_id=telegram_chat_id,
                message_thread_id=message_thread_id,
                topic_title=topic_title,
            )
        await self._record_command(
            "bind_chat",
            {"max_chat_id": max_chat_id, "telegram_chat_id": telegram_chat_id},
            actor=actor,
        )
        return (
            f"Bound `{binding.max_chat_id}` -> chat `{binding.telegram_chat_id}` "
            f"thread `{binding.message_thread_id}`."
        )

    async def unbind_chat(self, max_chat_id: str, *, actor: str | None = None) -> str:
        """Disable the active topic binding for one MAX chat."""

        await self.bridge_manager.unbind_chat(max_chat_id)
        await self._record_command("unbind_chat", {"max_chat_id": max_chat_id}, actor=actor)
        return f"Unbound `{max_chat_id}`."

    async def export_chat(self, chat_id: str, *, actor: str | None = None) -> str:
        """Export one chat archive and record the action."""

        path = await self.exporter.export_chat_json(chat_id)
        await self._record_command("export_chat", {"chat_id": chat_id}, actor=actor)
        return f"Exported `{chat_id}` to `{path}`."

    async def export_all(self, *, actor: str | None = None) -> str:
        """Export all locally indexed chats and record the action."""

        paths = await self.exporter.export_all_json()
        await self._record_command("export_all", {}, actor=actor)
        return f"Exported {len(paths)} chat archive(s)."

    async def send_to_max(self, chat_id: str, text: str, *, actor: str | None = None) -> str:
        """Send one deliberate outbound message via the local account."""

        message = await self.client.send_text_message(chat_id, text)
        await self._record_command("send_to_max", {"chat_id": chat_id}, actor=actor)
        return f"Sent message `{message.id}` to `{chat_id}`."

    async def react(
        self, chat_id: str, message_id: str, emoji: str, *, actor: str | None = None
    ) -> str:
        """Send one deliberate reaction via the local account."""

        reaction = await self.client.send_reaction(chat_id, message_id, emoji)
        await self._record_command(
            "react",
            {"chat_id": chat_id, "message_id": message_id, "emoji": emoji},
            actor=actor,
        )
        return f"Reaction `{reaction.emoji}` sent."

    async def typing(self, chat_id: str, *, enabled: bool, actor: str | None = None) -> str:
        """Toggle typing indication through the transport when supported."""

        await self.client.set_typing(chat_id, enabled=enabled)
        command = "typing_on" if enabled else "typing_off"
        await self._record_command(command, {"chat_id": chat_id}, actor=actor)
        return f"Typing {'enabled' if enabled else 'disabled'} for `{chat_id}`."

    async def set_target_forum(self, forum_chat_id: int, *, actor: str | None = None) -> str:
        """Update the runtime default forum chat ID.

        This changes the in-memory runtime only. The method intentionally does
        not rewrite the config file behind the user's back.
        """

        self.client.config.telegram.default_forum_chat_id = forum_chat_id
        await self._record_command(
            "set_target_forum", {"forum_chat_id": forum_chat_id}, actor=actor
        )
        return f"default_forum_chat_id set to `{forum_chat_id}` for this runtime."

    async def create_topics(self, *, actor: str | None = None) -> str:
        """Ensure topic bindings exist for all visible chats."""

        chats = await self.client.get_chats()
        created = 0
        for chat in chats:
            if await self.client.store.get_topic_binding(chat.id) is None:
                await self.bridge_manager.auto_bind_chat(max_chat_id=chat.id, topic_title=chat.title)
                created += 1
        await self._record_command("create_topics", {}, actor=actor)
        return f"Created {created} topic binding(s)."

    async def show_rules(self, *, actor: str | None = None) -> str:
        """Show the currently active routing rules."""

        bridge = self.client.config.bridge
        await self._record_command("show_rules", {}, actor=actor)
        return (
            f"selected_chat_ids={bridge.selected_chat_ids}\n"
            f"excluded_chat_ids={bridge.excluded_chat_ids}\n"
            f"skip_system_messages={bridge.skip_system_messages}"
        )

    async def not_implemented(self, command: str, *, actor: str | None = None) -> str:
        """Record and report a reserved command that is not implemented yet."""

        await self._record_command(command, {"status": "not_implemented"}, actor=actor)
        return f"`{command}` is reserved but not implemented in the MVP yet."

    async def _record_command(
        self, command: str, arguments: dict[str, object], *, actor: str | None
    ) -> None:
        """Persist command history and audit records.

        Command history captures operator intent. Audit records exist so the
        repository can support responsible owner-only automation without hidden
        side effects.
        """

        serialized_arguments = json.dumps(arguments, sort_keys=True, ensure_ascii=True)
        # Deterministic IDs make duplicate command handling easier to inspect.
        command_id = stable_id("cmd", command, actor or "system", serialized_arguments)
        await self.client.store.record_command(
            CommandHistoryRecord(
                id=command_id,
                source="telegram",
                actor=actor,
                command=command,
                arguments=arguments,
            )
        )
        if self.client.config.security.audit_log:
            await self.client.store.audit(
                AuditLogRecord(
                    id=stable_id("audit", command, actor or "system", command_id),
                    actor=actor,
                    action=command,
                    target=arguments.get("chat_id") if "chat_id" in arguments else None,
                    details=arguments,
                )
            )
