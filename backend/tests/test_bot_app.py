import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import select
from sqlalchemy.orm import sessionmaker
from telegram.ext import CallbackQueryHandler, CommandHandler

from app.bot import commands, messages
from app.bot.app import DONE_CALLBACK_PREFIX, BotHandlers, create_bot
from app.config import Settings
from app.models import Milestone, Project, User

ALLOWED_ID = 777
STRANGER_ID = 999


@pytest.fixture(autouse=True)
def settings(monkeypatch):
    monkeypatch.setattr(commands, "get_settings", lambda: Settings(max_active_projects=2))


@pytest.fixture
def handlers(session):
    factory = sessionmaker(bind=session.get_bind(), expire_on_commit=False)
    return BotHandlers(ALLOWED_ID, factory)


def message_update(user_id, text):
    return SimpleNamespace(
        effective_user=SimpleNamespace(id=user_id),
        message=SimpleNamespace(text=text, reply_text=AsyncMock()),
        callback_query=None,
    )


def callback_update(user_id, data):
    query = SimpleNamespace(data=data, answer=AsyncMock(), edit_message_text=AsyncMock())
    return SimpleNamespace(effective_user=SimpleNamespace(id=user_id), message=None, callback_query=query)


def run_command(handlers, name, update):
    handler = handlers._command(getattr(commands, name))
    asyncio.run(handler(update, None))


def test_allowed_user_gets_a_reply_and_data_is_stored_under_their_telegram_id(handlers, session):
    update = message_update(ALLOWED_ID, "/proyecto Mi Proyecto")

    run_command(handlers, "proyecto", update)

    update.message.reply_text.assert_awaited_once()
    assert "mi-proyecto" in update.message.reply_text.await_args.args[0]
    owner = session.scalar(select(User).where(User.telegram_id == ALLOWED_ID))
    assert session.scalar(select(Project)).user_id == owner.id


def test_stranger_is_ignored_in_silence(handlers, session):
    update = message_update(STRANGER_ID, "/proyecto Intruso")

    run_command(handlers, "proyecto", update)

    update.message.reply_text.assert_not_awaited()
    assert session.scalar(select(Project)) is None


def test_update_without_user_is_ignored(handlers):
    update = message_update(ALLOWED_ID, "/estado")
    update.effective_user = None

    run_command(handlers, "estado", update)

    update.message.reply_text.assert_not_awaited()


def test_command_args_keep_multiline_text(handlers, session):
    run_command(handlers, "proyecto", message_update(ALLOWED_ID, "/proyecto@KairosBot Uno\nDos"))

    assert session.scalar(select(Project)).name == "Uno\nDos"


def seed_milestones(handlers, titles):
    for text in ["/proyecto Kairos", *[f"/hito kairos: {t}" for t in titles]]:
        name = text.split()[0].lstrip("/")
        run_command(handlers, name, message_update(ALLOWED_ID, text))


def test_hecho_with_id_marks_the_milestone(handlers, session):
    seed_milestones(handlers, ["uno"])
    milestone = session.scalar(select(Milestone))
    update = message_update(ALLOWED_ID, f"/hecho {milestone.id}")

    asyncio.run(handlers.hecho(update, None))

    session.expire_all()
    assert session.get(Milestone, milestone.id).done
    assert "100%" in update.message.reply_text.await_args.args[0]


def test_hecho_without_argument_offers_pending_milestones_as_buttons(handlers, session):
    seed_milestones(handlers, ["uno", "dos"])
    first = session.scalars(select(Milestone).order_by(Milestone.id)).first()
    asyncio.run(handlers.hecho(message_update(ALLOWED_ID, f"/hecho {first.id}"), None))
    update = message_update(ALLOWED_ID, "/hecho")

    asyncio.run(handlers.hecho(update, None))

    keyboard = update.message.reply_text.await_args.kwargs["reply_markup"].inline_keyboard
    assert [[b.text for b in row] for row in keyboard] == [[f"#{first.id + 1} kairos: dos"]]
    assert keyboard[0][0].callback_data == f"{DONE_CALLBACK_PREFIX}{first.id + 1}"


def test_hecho_without_pending_milestones(handlers):
    update = message_update(ALLOWED_ID, "/hecho")

    asyncio.run(handlers.hecho(update, None))

    update.message.reply_text.assert_awaited_once_with(messages.NO_PENDING_MILESTONES)


def test_hecho_from_a_stranger_is_ignored(handlers, session):
    seed_milestones(handlers, ["uno"])
    update = message_update(STRANGER_ID, "/hecho")

    asyncio.run(handlers.hecho(update, None))

    update.message.reply_text.assert_not_awaited()


def test_callback_marks_the_milestone_and_edits_the_message(handlers, session):
    seed_milestones(handlers, ["uno"])
    milestone = session.scalar(select(Milestone))
    update = callback_update(ALLOWED_ID, f"{DONE_CALLBACK_PREFIX}{milestone.id}")

    asyncio.run(handlers.hecho_callback(update, None))

    session.expire_all()
    assert session.get(Milestone, milestone.id).done
    update.callback_query.answer.assert_awaited_once()
    assert "Hecho" in update.callback_query.edit_message_text.await_args.args[0]


def test_callback_from_a_stranger_is_ignored_in_silence(handlers, session):
    seed_milestones(handlers, ["uno"])
    milestone = session.scalar(select(Milestone))
    update = callback_update(STRANGER_ID, f"{DONE_CALLBACK_PREFIX}{milestone.id}")

    asyncio.run(handlers.hecho_callback(update, None))

    session.expire_all()
    assert not session.get(Milestone, milestone.id).done
    update.callback_query.answer.assert_not_awaited()
    update.callback_query.edit_message_text.assert_not_awaited()


@pytest.mark.parametrize("name", ["start", "ayuda"])
def test_start_and_ayuda_reply_with_help_to_the_allowed_user(handlers, name):
    update = message_update(ALLOWED_ID, f"/{name}")
    command = commands.ayuda
    asyncio.run(handlers._command(command)(update, None))

    update.message.reply_text.assert_awaited_once_with(messages.HELP)


@pytest.mark.parametrize("name", ["ayuda", "pausa", "terminar"])
def test_new_commands_ignore_strangers(handlers, session, name):
    update = message_update(STRANGER_ID, f"/{name} kairos")

    run_command(handlers, name, update)

    update.message.reply_text.assert_not_awaited()


def test_pausa_and_terminar_through_the_handler(handlers, session):
    run_command(handlers, "proyecto", message_update(ALLOWED_ID, "/proyecto Kairos"))
    pause = message_update(ALLOWED_ID, "/pausa kairos")
    finish = message_update(ALLOWED_ID, "/terminar kairos")

    run_command(handlers, "pausa", pause)
    session.expire_all()
    assert session.scalar(select(Project)).status.value == "paused"
    run_command(handlers, "terminar", finish)
    session.expire_all()
    assert session.scalar(select(Project)).status.value == "done"


def test_create_bot_registers_every_command_and_the_callback():
    application = create_bot(Settings(telegram_bot_token="123:fake", telegram_allowed_user_id=ALLOWED_ID))

    handlers = application.handlers[0]
    names = {c for h in handlers if isinstance(h, CommandHandler) for c in h.commands}
    assert names == {
        "proyecto", "idea", "hito", "hecho", "estado", "foco", "decision",
        "pausa", "terminar", "exportar", "ayuda", "start",
    }
    assert any(isinstance(h, CallbackQueryHandler) for h in handlers)


@pytest.mark.parametrize(
    "token, user_id", [("", ALLOWED_ID), ("123:fake", None), ("", None)]
)
def test_create_bot_is_disabled_without_full_configuration(token, user_id, caplog):
    settings = Settings(telegram_bot_token=token, telegram_allowed_user_id=user_id)

    assert create_bot(settings) is None
    assert "Telegram bot disabled" in caplog.text



def test_exportar_through_the_handler_replies_to_the_allowed_user_only(handlers, monkeypatch, tmp_path):
    vault = tmp_path / "vault"
    vault.mkdir()
    monkeypatch.setattr(commands, "get_settings", lambda: Settings(obsidian_vault_path=str(vault)))
    run_command(handlers, "proyecto", message_update(ALLOWED_ID, "/proyecto Kairos"))
    allowed = message_update(ALLOWED_ID, "/exportar")
    stranger = message_update(STRANGER_ID, "/exportar")

    run_command(handlers, "exportar", allowed)
    run_command(handlers, "exportar", stranger)

    assert allowed.message.reply_text.await_args.args[0].startswith("Export listo: 1 proyecto")
    stranger.message.reply_text.assert_not_awaited()
    assert (vault / "Kairos" / "kairos" / "README.md").is_file()
