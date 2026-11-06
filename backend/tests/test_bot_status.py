import logging
from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from app import main
from app.bot import app as bot_app
from app.bot.status import BotState, BotStatus
from app.config import Settings
from tests.test_bot_lifecycle import fake_application

NOW = datetime(2026, 11, 5, 12, 0, tzinfo=UTC)


def run_app(monkeypatch, settings: Settings, application=None):
    """Start the app (and the fake bot) and return (status while running, status after shutdown)."""
    if application is not None:
        monkeypatch.setattr(bot_app, "create_bot", lambda *_: application)
    monkeypatch.setattr(main, "get_settings", lambda: settings)
    app = main.create_app()
    app.state.bot_status = BotStatus(clock=lambda: NOW)
    with TestClient(app):
        running = app.state.bot_status.snapshot
    return running, app.state.bot_status.snapshot


def test_status_starts_stopped():
    assert BotStatus().snapshot.status is BotState.STOPPED


@pytest.mark.parametrize(
    ("settings", "reason"),
    [
        (Settings(telegram_bot_token="", telegram_allowed_user_id=1), "missing_token"),
        (Settings(telegram_bot_token="123:fake", telegram_allowed_user_id=None), "missing_user_id"),
        (Settings(telegram_bot_token="", telegram_allowed_user_id=None), "missing_token"),
    ],
)
def test_unconfigured_bot_is_disabled_with_a_code(monkeypatch, settings, reason):
    during, after = run_app(monkeypatch, settings)

    assert during.status is BotState.DISABLED
    assert during.reason == reason
    assert after.status is BotState.DISABLED


def test_started_bot_is_running_with_start_time_then_stopped(monkeypatch):
    settings = Settings(telegram_bot_token="123:fake", telegram_allowed_user_id=1)

    during, after = run_app(monkeypatch, settings, fake_application())

    assert (during.status, during.reason, during.started_at) == (BotState.RUNNING, None, NOW)
    assert after.status is BotState.STOPPED
    assert after.started_at == NOW


def test_failed_start_records_only_the_exception_name_and_never_the_secret(monkeypatch, caplog):
    secret = "123:SECRET-TOKEN"
    application = fake_application(initialize=AsyncMock(side_effect=RuntimeError(f"bad {secret}")))
    application.updater.running = False
    application.running = False

    with caplog.at_level(logging.DEBUG):
        during, after = run_app(
            monkeypatch, Settings(telegram_bot_token=secret, telegram_allowed_user_id=1), application
        )

    assert (during.status, during.reason, during.started_at) == (BotState.FAILED, "RuntimeError", None)
    assert after.status is BotState.FAILED
    assert secret not in repr(during)
    assert secret not in caplog.text


def test_a_start_polling_failure_after_initialize_is_failed_too(monkeypatch):
    application = fake_application()
    application.updater.start_polling = AsyncMock(side_effect=OSError("boom"))

    during, _ = run_app(
        monkeypatch, Settings(telegram_bot_token="123:fake", telegram_allowed_user_id=1), application
    )

    assert (during.status, during.reason) == (BotState.FAILED, "OSError")
