"""Telegram wiring: thin async handlers around app.bot.commands, plus the polling lifecycle."""

import asyncio
import logging
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from typing import TypeVar

from sqlalchemy.orm import Session
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, ApplicationBuilder, CallbackQueryHandler, CommandHandler, ContextTypes

from app.bot import commands, messages
from app.config import Settings
from app.db import SessionLocal
from app.services.user_service import UserService

logger = logging.getLogger(__name__)

DONE_CALLBACK_PREFIX = "hecho:"
# Telegram caps inline keyboards at 100 buttons; keep it readable
MAX_KEYBOARD_BUTTONS = 30
MAX_BUTTON_LABEL = 60

T = TypeVar("T")
Command = Callable[[Session, int, str], str]
SessionFactory = Callable[[], Session]


class BotHandlers:
    """Handlers for the single allowed user; anyone else is ignored without a reply."""

    def __init__(self, allowed_user_id: int, session_factory: SessionFactory = SessionLocal) -> None:
        self._allowed_user_id = allowed_user_id
        self._session_factory = session_factory

    def register(self, application: Application) -> None:
        for name in ("proyecto", "idea", "hito", "foco", "decision", "estado", "pausa", "terminar", "exportar", "ayuda"):
            application.add_handler(CommandHandler(name, self._command(getattr(commands, name))))
        application.add_handler(CommandHandler("start", self._command(commands.ayuda)))
        application.add_handler(CommandHandler("hecho", self.hecho))
        application.add_handler(
            CallbackQueryHandler(self.hecho_callback, pattern=f"^{DONE_CALLBACK_PREFIX}")
        )

    def _is_allowed(self, update: Update) -> bool:
        user = update.effective_user
        return user is not None and user.id == self._allowed_user_id

    def _command(self, command: Command):
        async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
            if not self._is_allowed(update) or update.message is None:
                return
            reply = await self._run(command, _command_args(update.message.text))
            await update.message.reply_text(reply)

        return handler

    async def hecho(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not self._is_allowed(update) or update.message is None:
            return
        args = _command_args(update.message.text)
        if args:
            await update.message.reply_text(await self._run(commands.hecho, args))
            return
        pending = await self._run(lambda session, user_id, _: commands.pending_milestones(session, user_id))
        if not pending:
            await update.message.reply_text(messages.NO_PENDING_MILESTONES)
            return
        await update.message.reply_text(messages.PICK_MILESTONE, reply_markup=_keyboard(pending))

    async def hecho_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        query = update.callback_query
        if not self._is_allowed(update) or query is None:
            return
        await query.answer()
        milestone_id = (query.data or "").removeprefix(DONE_CALLBACK_PREFIX)
        await query.edit_message_text(await self._run(commands.hecho, milestone_id))

    async def _run(self, command: Callable[[Session, int, str], T], args: str = "") -> T:
        return await asyncio.to_thread(self._execute, command, args)

    def _execute(self, command: Callable[[Session, int, str], T], args: str) -> T:
        # One session per command, opened and closed in the worker thread that uses it
        with self._session_factory() as session:
            user = UserService.get_or_create_user(session, self._allowed_user_id)
            return command(session, user.id, args)


def _command_args(text: str | None) -> str:
    parts = (text or "").split(maxsplit=1)
    return parts[1] if len(parts) > 1 else ""


def _keyboard(pending: list[tuple[int, str]]) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(f"#{mid} {label}"[:MAX_BUTTON_LABEL], callback_data=f"{DONE_CALLBACK_PREFIX}{mid}")]
        for mid, label in pending[:MAX_KEYBOARD_BUTTONS]
    ]
    return InlineKeyboardMarkup(rows)


def create_bot(settings: Settings, session_factory: SessionFactory = SessionLocal) -> Application | None:
    """Build the polling application, or None (with a warning) if it is not configured."""
    if not settings.telegram_bot_token or settings.telegram_allowed_user_id is None:
        logger.warning(
            "Telegram bot disabled: set TELEGRAM_BOT_TOKEN and TELEGRAM_ALLOWED_USER_ID to enable it"
        )
        return None
    # httpx logs every request URL at INFO, and Telegram URLs embed the token
    for noisy in ("httpx", "httpcore"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
    application = ApplicationBuilder().token(settings.telegram_bot_token).build()
    BotHandlers(settings.telegram_allowed_user_id, session_factory).register(application)
    return application


@asynccontextmanager
async def bot_lifespan(
    settings: Settings, session_factory: SessionFactory = SessionLocal
) -> AsyncIterator[None]:
    """Run the bot's long polling for the duration of the context; the API never depends on it."""
    application = create_bot(settings, session_factory)
    started = False
    if application is not None:
        try:
            await application.initialize()
            await application.start()
            await application.updater.start_polling()
            started = True
            logger.info("Telegram bot started")
        except Exception as error:
            # Only the class name: some Telegram errors echo the token in their message
            logger.error("Telegram bot failed to start (%s); the API keeps running", type(error).__name__)
            await _shutdown(application)
    try:
        yield
    finally:
        if started:
            await _shutdown(application)


async def _shutdown(application: Application) -> None:
    try:
        if application.updater.running:
            await application.updater.stop()
        if application.running:
            await application.stop()
        await application.shutdown()
    except Exception as error:
        logger.error("Telegram bot did not stop cleanly (%s)", type(error).__name__)
