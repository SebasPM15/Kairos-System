"""Proactive messages: the one place besides the command handlers that talks to Telegram."""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application

from app.bot import messages
from app.bot.status import BotStatus
from app.services.reminder_digest import Digest


SNOOZE_CALLBACK_PREFIX = "pos:"
MUTE_CALLBACK_PREFIX = "sil:"


def reminder_keyboard(digest: Digest) -> InlineKeyboardMarkup | None:
    """One row per listed project, numbered like the text; paused projects have no buttons."""
    rows = [
        [
            InlineKeyboardButton(
                f"{n}. Posponer {messages.SNOOZE_BUTTON_DAYS} d", callback_data=f"{SNOOZE_CALLBACK_PREFIX}{alert.project_id}"
            ),
            InlineKeyboardButton(f"{n}. Silenciar", callback_data=f"{MUTE_CALLBACK_PREFIX}{alert.project_id}"),
        ]
        for n, alert in enumerate(digest.items, start=1)
    ]
    return InlineKeyboardMarkup(rows) if rows else None


class TelegramNotifier:
    def __init__(self, application: Application, status: BotStatus, stale_days_paused: int) -> None:
        self._application = application
        self._status = status
        self._stale_days_paused = stale_days_paused

    async def send_digest(self, chat_id: int, digest: Digest) -> None:
        """Raises whatever Telegram raises; the caller decides what a failure means."""
        text = messages.digest_text(digest, self._stale_days_paused)
        await self._application.bot.send_message(
            chat_id=chat_id, text=text, reply_markup=reminder_keyboard(digest)
        )
        self._status.message_sent()
