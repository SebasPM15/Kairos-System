import asyncio
import logging
from unittest.mock import AsyncMock, MagicMock

from telegram.ext import CommandHandler

from app.bot import commands, messages
from app.bot.app import create_bot, register_menu
from app.bot.catalog import COMMAND_CATALOG, help_text
from app.config import Settings


def test_catalog_has_no_duplicates_and_syntax_matches_the_name():
    names = [info.name for info in COMMAND_CATALOG]

    assert len(names) == len(set(names))
    assert "exportar" in names
    for info in COMMAND_CATALOG:
        assert info.syntax.split()[0] == f"/{info.name}"
        assert info.description


def test_telegram_menu_limits_are_respected():
    for info in COMMAND_CATALOG:
        assert info.name.islower() and len(info.name) <= 32
        assert 3 <= len(info.description) <= 256


def test_help_is_generated_from_the_catalog(session):
    reply = commands.ayuda(session, 1, "")

    assert reply == messages.HELP == help_text()
    for info in COMMAND_CATALOG:
        assert info.syntax in reply
        assert info.description in reply


def test_every_catalog_command_has_a_handler():
    application = create_bot(Settings(telegram_bot_token="123:fake", telegram_allowed_user_id=1))

    registered = {c for h in application.handlers[0] if isinstance(h, CommandHandler) for c in h.commands}
    assert registered == {info.name for info in COMMAND_CATALOG} | {"start"}


def test_endpoint_returns_the_catalog(client):
    response = client.get("/bot/commands")

    assert response.status_code == 200
    assert response.json() == [info.model_dump() for info in COMMAND_CATALOG]


def test_menu_is_registered_from_the_catalog():
    application = MagicMock()
    application.bot.set_my_commands = AsyncMock()

    asyncio.run(register_menu(application))

    (sent,) = application.bot.set_my_commands.await_args.args
    assert [(c.command, c.description) for c in sent] == [(i.name, i.description) for i in COMMAND_CATALOG]


def test_menu_failure_logs_only_the_exception_name(caplog):
    secret = "123:SECRET-TOKEN"
    application = MagicMock()
    application.bot.set_my_commands = AsyncMock(side_effect=RuntimeError(f"bad {secret}"))

    with caplog.at_level(logging.ERROR):
        asyncio.run(register_menu(application))

    assert "(RuntimeError)" in caplog.text
    assert secret not in caplog.text
