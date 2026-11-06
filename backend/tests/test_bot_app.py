import asyncio
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import select
from sqlalchemy.orm import sessionmaker
from telegram.ext import CallbackQueryHandler, CommandHandler

from app.bot import commands, messages
from app.bot.app import DONE_CALLBACK_PREFIX, BotHandlers, create_bot
from app.bot.status import BotStatus, BotStatusSnapshot
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
        "recordatorios", "posponer", "silenciar", "reactivar",
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


NOW = datetime(2026, 11, 5, 12, 0, tzinfo=UTC)


@pytest.fixture
def status():
    return BotStatus(clock=lambda: NOW)


@pytest.fixture
def tracked(session, status):
    factory = sessionmaker(bind=session.get_bind(), expire_on_commit=False)
    return BotHandlers(ALLOWED_ID, factory, status)


def test_a_reply_records_the_last_message_sent(tracked, status):
    run_command(tracked, "estado", message_update(ALLOWED_ID, "/estado"))

    assert status.snapshot.last_message_sent_at == NOW


def test_a_failed_reply_is_not_recorded(tracked, status):
    update = message_update(ALLOWED_ID, "/estado")
    update.message.reply_text = AsyncMock(side_effect=RuntimeError("network"))

    with pytest.raises(RuntimeError):
        run_command(tracked, "estado", update)

    assert status.snapshot.last_message_sent_at is None


def test_a_stranger_never_updates_the_status(tracked, status):
    run_command(tracked, "estado", message_update(STRANGER_ID, "/estado"))

    assert status.snapshot.last_message_sent_at is None


def test_keyboard_and_callback_replies_are_recorded(tracked, status):
    seed_milestones(tracked, ["uno"])
    status._snapshot = BotStatusSnapshot()
    update = message_update(ALLOWED_ID, "/hecho")

    asyncio.run(tracked.hecho(update, None))
    assert status.snapshot.last_message_sent_at == NOW

    status._snapshot = BotStatusSnapshot()
    milestone_id = f"{DONE_CALLBACK_PREFIX}1"
    asyncio.run(tracked.hecho_callback(callback_update(ALLOWED_ID, milestone_id), None))
    assert status.snapshot.last_message_sent_at == NOW


# --- digest buttons ---------------------------------------------------------------------------


def digest_keyboard(*project_ids):
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup

    from app.bot.notifier import MUTE_CALLBACK_PREFIX, SNOOZE_CALLBACK_PREFIX

    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("Posponer 7 d", callback_data=f"{SNOOZE_CALLBACK_PREFIX}{pid}"),
                InlineKeyboardButton("Silenciar", callback_data=f"{MUTE_CALLBACK_PREFIX}{pid}"),
            ]
            for pid in project_ids
        ]
    )


def button_update(user_id, data, *project_ids):
    update = callback_update(user_id, data)
    update.callback_query.message = SimpleNamespace(reply_markup=digest_keyboard(*project_ids))
    update.callback_query.edit_message_reply_markup = AsyncMock()
    return update


def prefs_for(session, project_id):
    from app.models import ProjectReminderPrefs

    session.expire_all()
    return session.get(ProjectReminderPrefs, project_id)


def make_two_projects(handlers, session):
    for name in ("Uno", "Dos"):
        run_command(handlers, "proyecto", message_update(ALLOWED_ID, f"/proyecto {name}"))
    return [p.id for p in session.scalars(select(Project).order_by(Project.id))]


def test_snooze_button_snoozes_answers_and_removes_only_that_project_buttons(handlers, session):
    first, second = make_two_projects(handlers, session)
    update = button_update(ALLOWED_ID, f"pos:{first}", first, second)

    asyncio.run(handlers.reminder_callback(update, None))

    assert prefs_for(session, first).snoozed_until is not None
    assert prefs_for(session, second) is None
    update.callback_query.answer.assert_awaited_once()
    assert "Uno" in update.callback_query.answer.await_args.args[0]
    (markup,) = update.callback_query.edit_message_reply_markup.await_args.args
    assert [b.callback_data for row in markup.inline_keyboard for b in row] == [f"pos:{second}", f"sil:{second}"]


def test_mute_button_mutes(handlers, session):
    first, second = make_two_projects(handlers, session)
    update = button_update(ALLOWED_ID, f"sil:{second}", first, second)

    asyncio.run(handlers.reminder_callback(update, None))

    assert prefs_for(session, second).muted is True
    assert prefs_for(session, first) is None
    assert "reactivar" in update.callback_query.answer.await_args.args[0]


def test_buttons_of_a_stranger_are_ignored_in_silence(handlers, session):
    first, second = make_two_projects(handlers, session)
    for data in (f"pos:{first}", f"sil:{first}"):
        update = button_update(STRANGER_ID, data, first, second)

        asyncio.run(handlers.reminder_callback(update, None))

        update.callback_query.answer.assert_not_awaited()
        update.callback_query.edit_message_reply_markup.assert_not_awaited()
    assert prefs_for(session, first) is None


def test_button_for_a_project_of_another_user_changes_nothing(handlers, session, users):
    foreign = Project(user_id=users[1].id, name="Theirs", slug="theirs")
    session.add(foreign)
    session.commit()
    update = button_update(ALLOWED_ID, f"sil:{foreign.id}", foreign.id)

    asyncio.run(handlers.reminder_callback(update, None))

    assert "No existe ese proyecto" in update.callback_query.answer.await_args.args[0]
    assert prefs_for(session, foreign.id) is None


def test_button_with_a_garbage_id_answers_generically(handlers, session):
    update = button_update(ALLOWED_ID, "pos:abc")

    asyncio.run(handlers.reminder_callback(update, None))

    assert update.callback_query.answer.await_args.args[0] == messages.UNEXPECTED_ERROR


def test_button_on_a_message_without_markup_still_answers(handlers, session):
    first, _ = make_two_projects(handlers, session)
    update = button_update(ALLOWED_ID, f"pos:{first}")
    update.callback_query.message = None

    asyncio.run(handlers.reminder_callback(update, None))

    update.callback_query.answer.assert_awaited_once()
    update.callback_query.edit_message_reply_markup.assert_not_awaited()


def test_reminder_buttons_are_registered_with_their_prefixes():
    application = create_bot(Settings(telegram_bot_token="123:fake", telegram_allowed_user_id=ALLOWED_ID))

    patterns = [h.pattern.pattern for h in application.handlers[0] if isinstance(h, CallbackQueryHandler)]
    assert "^(pos:|sil:)" in patterns
