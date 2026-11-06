import asyncio
import logging
import threading
from datetime import timedelta
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import sessionmaker
from telegram.error import NetworkError

from app import main
from app.bot import app as bot_app
from app.bot.notifier import TelegramNotifier
from app.bot.status import BotState, BotStatus
from app.config import Settings
from app.models import ReminderLog, User
from app.reminders import scheduler as scheduler_module
from app.reminders.scheduler import STARTUP_GRACE_SECONDS, TICK_SECONDS, ReminderScheduler, reminder_scheduler
from app.services.reminder_digest import Digest
from tests.test_bot_lifecycle import fake_application
from tests.test_reminder_service import NOW, Clock, add_project

TELEGRAM_ID = 777


class FakeNotifier:
    def __init__(self, error: Exception | None = None) -> None:
        self.sent: list[tuple[int, Digest]] = []
        self.error = error

    async def send_digest(self, chat_id: int, digest: Digest) -> None:
        if self.error:
            raise self.error
        self.sent.append((chat_id, digest))


@pytest.fixture
def owner(session):
    user = User(telegram_id=TELEGRAM_ID)
    session.add(user)
    session.commit()
    return user


@pytest.fixture
def clock():
    return Clock()


@pytest.fixture
def factory(session):
    return sessionmaker(bind=session.get_bind(), expire_on_commit=False)


@pytest.fixture
def status():
    bot_status = BotStatus()
    bot_status.running()
    return bot_status


@pytest.fixture
def settings():
    return Settings(telegram_bot_token="123:fake", telegram_allowed_user_id=TELEGRAM_ID)


def build(settings, notifier, status, factory, clock, sleep=None):
    kwargs = {"sleep": sleep} if sleep else {}
    return ReminderScheduler(settings, notifier, status, factory, clock, **kwargs)


def log_count(session) -> int:
    session.expire_all()
    return session.scalar(select(func.count()).select_from(ReminderLog))


def test_run_waits_the_grace_period_then_ticks_every_thirty_minutes_without_real_sleeping(
    session, owner, settings, status, factory, clock
):
    add_project(session, owner, "Old", idle=20)
    notifier = FakeNotifier()
    sleeps: list[float] = []

    async def fake_sleep(seconds):
        sleeps.append(seconds)
        if len(sleeps) == 3:
            raise asyncio.CancelledError

    scheduler = build(settings, notifier, status, factory, clock, fake_sleep)

    with pytest.raises(asyncio.CancelledError):
        asyncio.run(scheduler.run())

    assert sleeps == [STARTUP_GRACE_SECONDS, TICK_SECONDS, TICK_SECONDS]
    assert (STARTUP_GRACE_SECONDS, TICK_SECONDS) == (60, 1800)
    assert len(notifier.sent) == 1  # the second tick is the same local day
    assert notifier.sent[0][0] == TELEGRAM_ID


def test_tick_sends_to_the_allowed_telegram_user_and_logs_after_success(session, owner, settings, status, factory, clock):
    add_project(session, owner, "Old", idle=20)
    notifier = FakeNotifier()

    assert asyncio.run(build(settings, notifier, status, factory, clock).tick()) is True

    assert [a.slug for a in notifier.sent[0][1].items] == ["old"]
    assert log_count(session) == 1


@pytest.mark.parametrize("make_status", ["disabled", "failed", "stopped"])
def test_tick_delivers_nothing_while_the_bot_is_not_running(session, owner, settings, factory, clock, make_status):
    add_project(session, owner, "Old", idle=20)
    bot_status = BotStatus()
    if make_status == "disabled":
        bot_status.disabled("missing_token")
    elif make_status == "failed":
        bot_status.failed("InvalidToken")
    notifier = FakeNotifier()

    assert asyncio.run(build(settings, notifier, bot_status, factory, clock).tick()) is False

    assert notifier.sent == []
    assert log_count(session) == 0


def test_tick_without_an_allowed_user_does_nothing(session, owner, status, factory, clock):
    add_project(session, owner, "Old", idle=20)
    notifier = FakeNotifier()
    unconfigured = Settings(telegram_bot_token="123:fake", telegram_allowed_user_id=None)

    assert asyncio.run(build(unconfigured, notifier, status, factory, clock).tick()) is False
    assert notifier.sent == []


def test_a_failed_send_records_only_the_error_type_logs_nothing_and_is_retried(
    session, owner, settings, status, factory, clock, caplog
):
    secret = "123:SECRET-TOKEN"
    add_project(session, owner, "Old", idle=20)
    failing = FakeNotifier(error=NetworkError(f"cannot reach https://api.telegram.org/bot{secret}/sendMessage"))

    with caplog.at_level(logging.DEBUG):
        assert asyncio.run(build(settings, failing, status, factory, clock).tick()) is False

    assert log_count(session) == 0
    assert status.snapshot.status is BotState.RUNNING
    assert status.snapshot.last_error.type == "NetworkError"
    assert secret not in caplog.text
    assert secret not in repr(status.snapshot)

    clock.now = NOW + timedelta(minutes=30)
    working = FakeNotifier()
    assert asyncio.run(build(settings, working, status, factory, clock).tick()) is True
    assert log_count(session) == 1


def test_database_work_runs_off_the_event_loop_thread(session, owner, settings, status, clock, factory):
    add_project(session, owner, "Old", idle=20)
    threads: set[int] = set()

    def spying_factory():
        threads.add(threading.get_ident())
        return factory()

    asyncio.run(build(settings, FakeNotifier(), status, spying_factory, clock).tick())

    assert threads
    assert threading.get_ident() not in threads


def test_telegram_notifier_sends_the_digest_text_and_records_the_send(settings):
    application = fake_application()
    application.bot.send_message = AsyncMock()
    status = BotStatus()
    notifier = TelegramNotifier(application, status, stale_days_paused=30)
    digest = Digest(items=[], paused=[])

    asyncio.run(notifier.send_digest(TELEGRAM_ID, digest))

    kwargs = application.bot.send_message.await_args.kwargs
    assert kwargs["chat_id"] == TELEGRAM_ID
    assert kwargs["text"].startswith("Recordatorios")
    assert status.snapshot.last_message_sent_at is not None


def test_telegram_notifier_does_not_record_a_failed_send():
    application = fake_application()
    application.bot.send_message = AsyncMock(side_effect=NetworkError("x"))
    status = BotStatus()

    with pytest.raises(NetworkError):
        asyncio.run(TelegramNotifier(application, status, 30).send_digest(1, Digest(items=[], paused=[])))

    assert status.snapshot.last_message_sent_at is None


# --- lifespan -----------------------------------------------------------------------------


def test_scheduler_starts_after_the_bot_and_stops_before_it(monkeypatch, settings):
    order: list[str] = []
    application = fake_application()
    application.start = AsyncMock(side_effect=lambda: order.append("bot start"))
    application.stop = AsyncMock(side_effect=lambda: order.append("bot stop"))

    async def fake_run(self):
        order.append("scheduler start")
        try:
            await asyncio.sleep(3600)
        except asyncio.CancelledError:
            order.append("scheduler stop")
            raise

    monkeypatch.setattr(ReminderScheduler, "run", fake_run)
    monkeypatch.setattr(bot_app, "create_bot", lambda *_: application)
    monkeypatch.setattr(main, "get_settings", lambda: settings)

    with TestClient(main.create_app()):
        pass

    assert order == ["bot start", "scheduler start", "scheduler stop", "bot stop"]


@pytest.mark.parametrize(
    "configured",
    [
        Settings(telegram_bot_token="", telegram_allowed_user_id=1),  # bot disabled
        Settings(telegram_bot_token="123:fake", telegram_allowed_user_id=1, reminders_enabled=False),
    ],
    ids=["bot disabled", "reminders disabled"],
)
def test_no_scheduler_when_the_bot_or_the_reminders_are_off(monkeypatch, configured):
    started = []

    async def fake_run(self):
        started.append(True)

    monkeypatch.setattr(ReminderScheduler, "run", fake_run)
    monkeypatch.setattr(bot_app, "create_bot", lambda *_: fake_application() if configured.telegram_bot_token else None)
    monkeypatch.setattr(main, "get_settings", lambda: configured)

    with TestClient(main.create_app()):
        pass

    assert started == []


def test_no_scheduler_when_the_bot_failed_to_start(monkeypatch, settings):
    started = []

    async def fake_run(self):
        started.append(True)

    application = fake_application(initialize=AsyncMock(side_effect=RuntimeError("x")))
    application.updater.running = False
    application.running = False
    monkeypatch.setattr(ReminderScheduler, "run", fake_run)
    monkeypatch.setattr(bot_app, "create_bot", lambda *_: application)
    monkeypatch.setattr(main, "get_settings", lambda: settings)

    with TestClient(main.create_app()):
        pass

    assert started == []


def test_the_context_manager_cancels_the_task_even_when_the_body_raises(monkeypatch, settings):
    cancelled = []

    async def fake_run(self):
        try:
            await asyncio.sleep(3600)
        except asyncio.CancelledError:
            cancelled.append(True)
            raise

    monkeypatch.setattr(scheduler_module.ReminderScheduler, "run", fake_run)

    async def body():
        async with reminder_scheduler(settings, fake_application(), BotStatus()):
            await asyncio.sleep(0)
            raise RuntimeError("boom")

    with pytest.raises(RuntimeError):
        asyncio.run(body())

    assert cancelled == [True]
