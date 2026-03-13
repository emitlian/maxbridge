"""Owner-only Telegram control bot.

The bot is part of the stable core because it is the primary operator control
plane. It is intentionally conservative: every command is owner-gated, actions
are routed through the control-plane service, and no public control surface is
exposed.
"""

from __future__ import annotations

import asyncio
from typing import Any

from maxbridge.core.exceptions import CommandError, ConfigError
from maxbridge.telegram.control_plane import ControlPlaneService

try:  # pragma: no cover - exercised in integration environments
    from telegram import Update
    from telegram.ext import Application, ApplicationBuilder, CommandHandler, ContextTypes
except ImportError:  # pragma: no cover
    Update = Any
    Application = Any
    ApplicationBuilder = None
    CommandHandler = None
    ContextTypes = Any


class TelegramControlBot:
    """Telegram bot that controls the local MAXBRIDGE runtime."""

    def __init__(self, *, config, control_plane: ControlPlaneService) -> None:
        """Initialize the bot around validated runtime services."""

        self.config = config
        self.control_plane = control_plane
        self._application: Application | None = None

    async def run(self) -> None:
        """Start long-running Telegram polling.

        The method blocks until the process is cancelled. The MVP uses polling
        because it keeps local development and deployment simple.
        """

        application = self._build_application()
        self._application = application
        await application.initialize()
        await application.start()
        if application.updater is None:  # pragma: no cover
            raise RuntimeError("Telegram updater is unavailable.")
        await application.updater.start_polling(drop_pending_updates=False)
        try:
            await asyncio.Event().wait()
        finally:  # pragma: no cover
            await application.updater.stop()
            await application.stop()
            await application.shutdown()

    def _build_application(self) -> Application:
        """Create the Telegram application and register all handlers."""

        if ApplicationBuilder is None or CommandHandler is None:
            raise ConfigError("python-telegram-bot is not installed.")
        if self.config.telegram.bot_token is None or not self.config.telegram.bot_token.get_secret_value():
            raise ConfigError("telegram.bot_token is required to run the control bot.")

        application = ApplicationBuilder().token(
            self.config.telegram.bot_token.get_secret_value()
        ).build()

        # Every supported command is mapped explicitly so reviewers can see the
        # full public surface in one place.
        command_map = {
            "start": self._start,
            "help": self._help,
            "status": self._status,
            "health": self._health,
            "login_status": self._login_status,
            "list_chats": self._list_chats,
            "bindings": self._bindings,
            "bind_chat": self._bind_chat,
            "unbind_chat": self._unbind_chat,
            "sync_now": self._sync_now,
            "pause": self._pause,
            "resume": self._resume,
            "export_chat": self._export_chat,
            "export_all": self._export_all,
            "set_target_forum": self._set_target_forum,
            "create_topics": self._create_topics,
            "show_rules": self._show_rules,
            "add_rule": self._reserved,
            "remove_rule": self._reserved,
            "typing_on": self._typing_on,
            "typing_off": self._typing_off,
            "react": self._react,
            "send_to_max": self._send_to_max,
        }
        for command, handler in command_map.items():
            application.add_handler(CommandHandler(command, handler))
        return application

    async def _start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle ``/start`` by returning the help text."""

        if not await self._authorize_or_reply(update):
            return
        await self._reply_if_owner(update, await self._help_text(actor=self._actor(update)))

    async def _help(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle ``/help`` by returning the help text."""

        if not await self._authorize_or_reply(update):
            return
        await self._reply_if_owner(update, await self._help_text(actor=self._actor(update)))

    async def _status(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle ``/status``."""

        if not await self._authorize_or_reply(update):
            return
        await self._reply_if_owner(
            update, await self.control_plane.status_text(actor=self._actor(update))
        )

    async def _health(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle ``/health``."""

        if not await self._authorize_or_reply(update):
            return
        await self._reply_if_owner(
            update, await self.control_plane.health_text(actor=self._actor(update))
        )

    async def _login_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle ``/login_status``."""

        if not await self._authorize_or_reply(update):
            return
        await self._reply_if_owner(
            update, await self.control_plane.login_status_text(actor=self._actor(update))
        )

    async def _list_chats(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle ``/list_chats``."""

        if not await self._authorize_or_reply(update):
            return
        await self._reply_if_owner(
            update, await self.control_plane.list_chats_text(actor=self._actor(update))
        )

    async def _bindings(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle ``/bindings``."""

        if not await self._authorize_or_reply(update):
            return
        await self._reply_if_owner(
            update, await self.control_plane.bindings_text(actor=self._actor(update))
        )

    async def _sync_now(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle ``/sync_now``."""

        if not await self._authorize_or_reply(update):
            return
        await self._reply_if_owner(update, await self.control_plane.sync_now(actor=self._actor(update)))

    async def _pause(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle ``/pause``."""

        if not await self._authorize_or_reply(update):
            return
        await self._reply_if_owner(update, await self.control_plane.pause(actor=self._actor(update)))

    async def _resume(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle ``/resume``."""

        if not await self._authorize_or_reply(update):
            return
        await self._reply_if_owner(update, await self.control_plane.resume(actor=self._actor(update)))

    async def _bind_chat(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle ``/bind_chat``."""

        if not await self._authorize_or_reply(update):
            return
        self._ensure_args(context.args, minimum=2, usage="/bind_chat <max_chat_id> <telegram_chat_id> [thread_id] [topic_title]")
        max_chat_id = context.args[0]
        telegram_chat_id = int(context.args[1])
        thread_id: int | None = int(context.args[2]) if len(context.args) >= 3 else None
        title = " ".join(context.args[3:]) if len(context.args) >= 4 else None
        response = await self.control_plane.bind_chat(
            max_chat_id=max_chat_id,
            telegram_chat_id=telegram_chat_id,
            message_thread_id=thread_id,
            topic_title=title,
            actor=self._actor(update),
        )
        await self._reply_if_owner(update, response)

    async def _unbind_chat(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle ``/unbind_chat``."""

        if not await self._authorize_or_reply(update):
            return
        self._ensure_args(context.args, minimum=1, usage="/unbind_chat <max_chat_id>")
        await self._reply_if_owner(
            update,
            await self.control_plane.unbind_chat(context.args[0], actor=self._actor(update)),
        )

    async def _export_chat(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle ``/export_chat``."""

        if not await self._authorize_or_reply(update):
            return
        self._ensure_args(context.args, minimum=1, usage="/export_chat <max_chat_id>")
        await self._reply_if_owner(
            update,
            await self.control_plane.export_chat(context.args[0], actor=self._actor(update)),
        )

    async def _export_all(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle ``/export_all``."""

        if not await self._authorize_or_reply(update):
            return
        await self._reply_if_owner(
            update, await self.control_plane.export_all(actor=self._actor(update))
        )

    async def _set_target_forum(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle ``/set_target_forum``."""

        if not await self._authorize_or_reply(update):
            return
        self._ensure_args(context.args, minimum=1, usage="/set_target_forum <telegram_chat_id>")
        await self._reply_if_owner(
            update,
            await self.control_plane.set_target_forum(int(context.args[0]), actor=self._actor(update)),
        )

    async def _create_topics(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle ``/create_topics``."""

        if not await self._authorize_or_reply(update):
            return
        await self._reply_if_owner(
            update, await self.control_plane.create_topics(actor=self._actor(update))
        )

    async def _show_rules(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle ``/show_rules``."""

        if not await self._authorize_or_reply(update):
            return
        await self._reply_if_owner(
            update, await self.control_plane.show_rules(actor=self._actor(update))
        )

    async def _typing_on(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle ``/typing_on``."""

        if not await self._authorize_or_reply(update):
            return
        self._ensure_args(context.args, minimum=1, usage="/typing_on <max_chat_id>")
        await self._reply_if_owner(
            update,
            await self.control_plane.typing(
                context.args[0], enabled=True, actor=self._actor(update)
            ),
        )

    async def _typing_off(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle ``/typing_off``."""

        if not await self._authorize_or_reply(update):
            return
        self._ensure_args(context.args, minimum=1, usage="/typing_off <max_chat_id>")
        await self._reply_if_owner(
            update,
            await self.control_plane.typing(
                context.args[0], enabled=False, actor=self._actor(update)
            ),
        )

    async def _react(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle ``/react``."""

        if not await self._authorize_or_reply(update):
            return
        self._ensure_args(context.args, minimum=3, usage="/react <max_chat_id> <message_id> <emoji>")
        await self._reply_if_owner(
            update,
            await self.control_plane.react(
                context.args[0],
                context.args[1],
                context.args[2],
                actor=self._actor(update),
            ),
        )

    async def _send_to_max(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle ``/send_to_max``."""

        if not await self._authorize_or_reply(update):
            return
        self._ensure_args(context.args, minimum=2, usage="/send_to_max <max_chat_id> <text>")
        await self._reply_if_owner(
            update,
            await self.control_plane.send_to_max(
                context.args[0],
                " ".join(context.args[1:]),
                actor=self._actor(update),
            ),
        )

    async def _reserved(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle reserved commands that exist in the public surface but not yet in the MVP."""

        if not await self._authorize_or_reply(update):
            return
        command = update.effective_message.text.split(" ")[0].lstrip("/") if update.effective_message else "reserved"
        await self._reply_if_owner(
            update, await self.control_plane.not_implemented(command, actor=self._actor(update))
        )

    async def _reply_if_owner(self, update: Update, text: str) -> None:
        """Send a response only when the caller is authorized.

        This method keeps the final send path owner-gated even when a handler
        has already performed an authorization check.
        """

        if not self._is_owner(update):
            if update.effective_message is not None:
                await update.effective_message.reply_text("Access denied.")
            return
        if update.effective_message is not None:
            await update.effective_message.reply_text(text, parse_mode=self.config.telegram.parse_mode)

    def _is_owner(self, update: Update) -> bool:
        """Return whether the Telegram user is allowed to control the bot."""

        user = update.effective_user
        if user is None:
            return False
        if not self.config.telegram.owner_user_ids:
            return not self.config.security.require_owner_allowlist
        return int(user.id) in self.config.telegram.owner_user_ids

    async def _authorize_or_reply(self, update: Update) -> bool:
        """Gate a command and send a denial message when needed."""

        if self._is_owner(update):
            return True
        if update.effective_message is not None:
            await update.effective_message.reply_text("Access denied.")
        return False

    def _actor(self, update: Update) -> str | None:
        """Return the actor ID string used by command/audit storage."""

        user = update.effective_user
        return str(user.id) if user is not None else None

    @staticmethod
    def _ensure_args(args: list[str], *, minimum: int, usage: str) -> None:
        """Raise a command error when not enough arguments were supplied."""

        if len(args) < minimum:
            raise CommandError(usage)

    async def _help_text(self, *, actor: str | None) -> str:
        """Return the static help text and record the help access."""

        await self.control_plane.not_implemented("help", actor=actor)
        return (
            "Commands:\n"
            "/status\n"
            "/health\n"
            "/login_status\n"
            "/list_chats\n"
            "/bindings\n"
            "/bind_chat <max_chat_id> <telegram_chat_id> [thread_id] [topic_title]\n"
            "/unbind_chat <max_chat_id>\n"
            "/sync_now\n"
            "/pause\n"
            "/resume\n"
            "/export_chat <max_chat_id>\n"
            "/export_all\n"
            "/set_target_forum <telegram_chat_id>\n"
            "/create_topics\n"
            "/show_rules\n"
            "/typing_on <max_chat_id>\n"
            "/typing_off <max_chat_id>\n"
            "/react <max_chat_id> <message_id> <emoji>\n"
            "/send_to_max <max_chat_id> <text>"
        )
