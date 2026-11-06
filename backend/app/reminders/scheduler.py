"""Background loop that delivers the daily reminder digest. Plain asyncio in the API process: no
scheduler dependency, and it relies on the same single-worker rule as the bot's long polling."""

import asyncio
import contextlib
import logging
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Protocol

from sqlalchemy.orm import Session
from telegram.ext import Application

from app.bot.notifier import TelegramNotifier
from app.bot.status import BotState, BotStatus
from app.config import Settings
from app.db import SessionLocal
from app.models.base import utcnow
from app.services.reminder_digest import Digest, deliver_digest
from app.services.user_service import UserService

logger = logging.getLogger(__name__)

TICK_SECONDS = 30 * 60
# Lets a restart (or a --reload cycle) settle before the first check
STARTUP_GRACE_SECONDS = 60

SessionFactory = Callable[[], Session]


class Notifier(Protocol):
    async def send_digest(self, chat_id: int, digest: Digest) -> None: ...


class ReminderScheduler:
    def __init__(
        self,
        settings: Settings,
        notifier: Notifier,
        status: BotStatus,
        session_factory: SessionFactory = SessionLocal,
        clock: Callable[[], datetime] = utcnow,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ) -> None:
        self._settings = settings
        self._notifier = notifier
        self._status = status
        self._session_factory = session_factory
        self._clock = clock
        self._sleep = sleep

    async def run(self) -> None:
        await self._sleep(STARTUP_GRACE_SECONDS)
        while True:
            await self.tick()
            await self._sleep(TICK_SECONDS)

    async def tick(self) -> bool:
        """One check; True when a digest went out. Never raises: a failing tick is retried at the next."""
        # Without a running bot there is nobody to deliver; the dashboard still shows the alerts
        if self._status.snapshot.status is not BotState.RUNNING:
            return False
        telegram_id = self._settings.telegram_allowed_user_id
        if telegram_id is None:
            return False
        try:
            user_id = await asyncio.to_thread(self._user_id, telegram_id)
            sent = await deliver_digest(
                user_id,
                session_factory=self._session_factory,
                settings=self._settings,
                clock=self._clock,
                send=lambda digest: self._notifier.send_digest(telegram_id, digest),
            )
        except Exception as error:
            # Only the class name: Telegram errors can echo the token
            logger.error("Reminder delivery failed (%s); it will be retried", type(error).__name__)
            self._status.record_error(error)
            return False
        if sent:
            logger.info("Reminder digest sent")
        return sent

    def _user_id(self, telegram_id: int) -> int:
        with self._session_factory() as session:
            return UserService.get_or_create_user(session, telegram_id).id


@asynccontextmanager
async def reminder_scheduler(
    settings: Settings,
    application: Application | None,
    status: BotStatus,
    session_factory: SessionFactory = SessionLocal,
) -> AsyncIterator[None]:
    """Runs for the duration of the context, started after the bot and stopped before it."""
    if application is None or not settings.reminders_enabled:
        yield
        return
    notifier = TelegramNotifier(application, status, settings.stale_days_paused)
    scheduler = ReminderScheduler(settings, notifier, status, session_factory)
    task = asyncio.create_task(scheduler.run())
    try:
        yield
    finally:
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task
