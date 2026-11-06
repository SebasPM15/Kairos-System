"""Proactive messages: the one place besides the command handlers that talks to Telegram."""

from telegram.ext import Application

from app.bot import messages
from app.bot.status import BotStatus
from app.services.reminder_digest import Digest


class TelegramNotifier:
    def __init__(self, application: Application, status: BotStatus, stale_days_paused: int) -> None:
        self._application = application
        self._status = status
        self._stale_days_paused = stale_days_paused

    async def send_digest(self, chat_id: int, digest: Digest) -> None:
        """Raises whatever Telegram raises; the caller decides what a failure means."""
        text = messages.digest_text(digest, self._stale_days_paused)
        await self._application.bot.send_message(chat_id=chat_id, text=text)
        self._status.message_sent()
