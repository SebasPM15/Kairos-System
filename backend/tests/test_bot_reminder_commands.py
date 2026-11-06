from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from app.bot import commands, messages
from app.bot.catalog import COMMAND_CATALOG
from app.config import Settings
from app.models import Milestone, Project, ProjectReminderPrefs, ProjectStatus


@pytest.fixture(autouse=True)
def settings(monkeypatch):
    monkeypatch.setattr(commands, "get_settings", lambda: Settings(max_active_projects=3))


@pytest.fixture
def me(users):
    return users[0].id


def make_project(session, user_id, name="Rust", status=ProjectStatus.ACTIVE, idle=0, milestones=0, done=0):
    project = Project(
        user_id=user_id,
        name=name,
        slug=name.lower().replace(" ", "-"),
        status=status,
        next_action="go",
        last_activity_at=datetime.now(UTC) - timedelta(days=idle),
    )
    session.add(project)
    session.flush()
    for position in range(milestones):
        session.add(Milestone(project_id=project.id, title=f"m{position}", done=position < done, position=position))
    session.commit()
    return project


def prefs_of(session, project):
    session.expire_all()
    return session.scalar(select(ProjectReminderPrefs).where(ProjectReminderPrefs.project_id == project.id))


def test_the_four_commands_are_in_the_catalog_with_spanish_text():
    by_name = {info.name: info for info in COMMAND_CATALOG}

    assert by_name["recordatorios"].syntax == "/recordatorios"
    assert by_name["posponer"].syntax == "/posponer <slug>: <días>"
    assert by_name["silenciar"].syntax == "/silenciar <slug>"
    assert by_name["reactivar"].syntax == "/reactivar <slug>"
    for name in ("recordatorios", "posponer", "silenciar", "reactivar"):
        assert by_name[name].description and callable(getattr(commands, name))


def test_every_catalog_command_has_a_function_in_commands():
    assert [i.name for i in COMMAND_CATALOG if not callable(getattr(commands, i.name, None))] == []


def test_recordatorios_without_anything_pending(session, me):
    make_project(session, me, idle=1)

    assert commands.recordatorios(session, me, "") == messages.NO_REMINDERS


def test_recordatorios_lists_alerts_and_the_suppressed(session, me):
    make_project(session, me, "Rust", idle=12)
    ready = make_project(session, me, "Portafolio", idle=1, milestones=2, done=2)
    muted = make_project(session, me, "Blog", status=ProjectStatus.PAUSED, idle=47)
    commands.silenciar(session, me, muted.slug)

    reply = commands.recordatorios(session, me, "")

    lines = reply.splitlines()
    assert lines[0] == "Recordatorios"
    assert lines[1] == "1. rust: 12 días sin avance. Aún no tiene hitos. Próxima acción: go"
    assert lines[2].startswith(f"2. {ready.slug}: todos los hitos están hechos.")
    assert "Pospuestos o silenciados:" in lines
    assert "- blog: silenciado" in lines
    assert lines[-1] == "Usa /reactivar <slug> para volver a recibirlos."


def test_recordatorios_with_only_suppressed_projects(session, me):
    project = make_project(session, me, "Rust", idle=12)
    commands.posponer(session, me, "rust: 3")

    reply = commands.recordatorios(session, me, "")

    assert reply.splitlines()[0] == "No hay recordatorios pendientes."
    assert "- rust: pospuesto hasta el " in reply
    assert project.slug in reply


def test_posponer_sets_the_snooze_and_confirms_with_the_date(session, me):
    project = make_project(session, me, "Rust", idle=12)

    reply = commands.posponer(session, me, "rust: 7")

    assert reply.startswith("Recordatorios de Rust pospuestos 7 días, hasta el ")
    until = prefs_of(session, project).snoozed_until
    assert timedelta(days=6, hours=23) < until - datetime.now(UTC) <= timedelta(days=7)


def test_posponer_one_day_is_singular(session, me):
    make_project(session, me, "Rust")

    assert "pospuestos 1 día," in commands.posponer(session, me, "rust: 1")


@pytest.mark.parametrize("args", ["rust: 0", "rust: 31", "rust: -2", "rust: muchos", "rust: 3.5"])
def test_posponer_rejects_days_outside_1_to_30(session, me, args):
    project = make_project(session, me, "Rust")

    assert commands.posponer(session, me, args) == messages.INVALID_SNOOZE_DAYS
    assert prefs_of(session, project) is None


@pytest.mark.parametrize("args", ["", "rust", "rust:", ": 3"])
def test_posponer_without_slug_or_days_shows_usage(session, me, args):
    assert commands.posponer(session, me, args) == messages.USAGE["posponer"]


def test_silenciar_mutes_and_tells_how_to_undo(session, me):
    project = make_project(session, me, "Rust")

    reply = commands.silenciar(session, me, "rust")

    assert prefs_of(session, project).muted is True
    assert reply == "Recordatorios de Rust silenciados. Para volver a recibirlos usa /reactivar rust."


def test_reactivar_clears_mute_and_snooze(session, me):
    project = make_project(session, me, "Rust", idle=12)
    commands.silenciar(session, me, "rust")
    commands.posponer(session, me, "rust: 5")

    reply = commands.reactivar(session, me, "rust")

    prefs = prefs_of(session, project)
    assert (prefs.muted, prefs.snoozed_until) == (False, None)
    assert reply == "Recordatorios de Rust reactivados."


@pytest.mark.parametrize("name", ["silenciar", "reactivar"])
def test_slug_commands_show_usage_without_an_argument(session, me, name):
    assert getattr(commands, name)(session, me, "  ") == messages.USAGE[name]


@pytest.mark.parametrize("name", ["posponer", "silenciar", "reactivar"])
def test_unknown_slug_gets_the_standard_message(session, me, name):
    args = "nada: 3" if name == "posponer" else "nada"

    assert getattr(commands, name)(session, me, args) == messages.error_message(
        __import__("app.services.errors", fromlist=["ProjectNotFound"]).ProjectNotFound("nada")
    )


@pytest.mark.parametrize("name", ["posponer", "silenciar", "reactivar"])
def test_another_users_project_cannot_be_touched(session, users, me, name):
    foreign = make_project(session, users[1].id, "Theirs", idle=12)
    args = "theirs: 3" if name == "posponer" else "theirs"

    reply = getattr(commands, name)(session, me, args)

    assert "No existe ese proyecto" in reply
    assert prefs_of(session, foreign) is None


def test_slug_is_case_insensitive(session, me):
    project = make_project(session, me, "Rust")

    commands.silenciar(session, me, "RUST")

    assert prefs_of(session, project).muted is True
