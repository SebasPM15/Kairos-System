import logging
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from app import main
from app.bot import app as bot_app
from app.config import Settings


def test_api_starts_without_bot_configuration(monkeypatch, caplog):
    monkeypatch.setattr(main, "get_settings", lambda: Settings(telegram_bot_token="", telegram_allowed_user_id=None))

    with caplog.at_level(logging.WARNING), TestClient(main.create_app()) as client:
        assert client.get("/health").status_code == 200

    assert "Telegram bot disabled" in caplog.text


def fake_application(**overrides):
    application = MagicMock()
    application.initialize = AsyncMock()
    application.start = AsyncMock()
    application.stop = AsyncMock()
    application.shutdown = AsyncMock()
    application.updater.start_polling = AsyncMock()
    application.updater.stop = AsyncMock()
    application.updater.running = True
    application.running = True
    for name, value in overrides.items():
        setattr(application, name, value)
    return application


def test_bot_is_started_and_stopped_with_the_app(monkeypatch):
    application = fake_application()
    monkeypatch.setattr(bot_app, "create_bot", lambda *_: application)
    monkeypatch.setattr(main, "get_settings", lambda: Settings(telegram_bot_token="123:fake", telegram_allowed_user_id=1))

    with TestClient(main.create_app()) as client:
        application.updater.start_polling.assert_awaited_once()
        application.updater.stop.assert_not_awaited()
        assert client.get("/health").status_code == 200

    application.updater.stop.assert_awaited_once()
    application.stop.assert_awaited_once()
    application.shutdown.assert_awaited_once()


def test_api_survives_a_bot_that_fails_to_start_and_never_logs_the_error_text(monkeypatch, caplog):
    secret = "123:SECRET-TOKEN"
    application = fake_application(initialize=AsyncMock(side_effect=RuntimeError(f"bad {secret}")))
    application.updater.running = False
    application.running = False
    monkeypatch.setattr(bot_app, "create_bot", lambda *_: application)
    monkeypatch.setattr(main, "get_settings", lambda: Settings(telegram_bot_token=secret, telegram_allowed_user_id=1))

    with caplog.at_level(logging.ERROR), TestClient(main.create_app()) as client:
        assert client.get("/health").status_code == 200

    assert "failed to start (RuntimeError)" in caplog.text
    assert secret not in caplog.text
    application.start.assert_not_awaited()


@pytest.mark.parametrize("logger_name", ["httpx", "httpcore"])
def test_create_bot_silences_loggers_that_print_the_token(logger_name):
    logging.getLogger(logger_name).setLevel(logging.INFO)

    bot_app.create_bot(Settings(telegram_bot_token="123:fake", telegram_allowed_user_id=1))

    assert logging.getLogger(logger_name).level == logging.WARNING
