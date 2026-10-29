import pytest
from sqlalchemy import select

from app.bot import commands, messages
from app.config import Settings
from app.models import Decision, Idea, Milestone, Project, ProjectStatus
from app.services.errors import ActiveLimitReached, MilestoneNotFound, ProjectNotFound


@pytest.fixture(autouse=True)
def settings(monkeypatch):
    monkeypatch.setattr(commands, "get_settings", lambda: Settings(max_active_projects=2))


@pytest.fixture
def me(users):
    return users[0].id


def make_project(session, user_id, name="Kairos"):
    commands.proyecto(session, user_id, name)
    return session.scalar(
        select(Project).where(Project.user_id == user_id, Project.name == name)
    )


def test_proyecto_creates_it_as_idea(session, me):
    reply = commands.proyecto(session, me, "Mi Proyecto")

    project = session.scalar(select(Project))
    assert project.slug == "mi-proyecto"
    assert project.status is ProjectStatus.IDEA
    assert "mi-proyecto" in reply


def test_proyecto_without_name_shows_usage(session, me):
    assert commands.proyecto(session, me, "  ") == messages.USAGE["proyecto"]


def test_proyecto_name_too_long_is_invalid_input(session, me):
    assert commands.proyecto(session, me, "x" * 201) == messages.INVALID_INPUT


def test_idea_with_known_slug_goes_to_the_project(session, me):
    project = make_project(session, me)

    reply = commands.idea(session, me, "kairos: usar webhooks")

    idea = session.scalar(select(Idea))
    assert (idea.project_id, idea.content) == (project.id, "usar webhooks")
    assert "kairos" in reply


def test_idea_without_slug_goes_to_the_inbox(session, me):
    make_project(session, me)

    reply = commands.idea(session, me, "algo suelto")

    idea = session.scalar(select(Idea))
    assert (idea.project_id, idea.content) == (None, "algo suelto")
    assert "bandeja" in reply


def test_idea_with_unknown_slug_keeps_the_whole_text(session, me):
    commands.idea(session, me, "nope: algo")

    idea = session.scalar(select(Idea))
    assert (idea.project_id, idea.content) == (None, "nope: algo")


def test_idea_empty_shows_usage(session, me):
    assert commands.idea(session, me, "") == messages.USAGE["idea"]


def test_hito_creates_and_reports_its_id(session, me):
    make_project(session, me)

    reply = commands.hito(session, me, "kairos: Bot listo")

    milestone = session.scalar(select(Milestone))
    assert milestone.title == "Bot listo"
    assert f"#{milestone.id}" in reply


def test_hito_unknown_slug(session, me):
    assert commands.hito(session, me, "nope: x") == messages.error_message(ProjectNotFound())
    assert session.scalar(select(Milestone)) is None


def test_hito_bad_format_shows_usage(session, me):
    assert commands.hito(session, me, "sin dos puntos") == messages.USAGE["hito"]


def test_hecho_marks_done_and_reports_progress(session, me):
    make_project(session, me)
    commands.hito(session, me, "kairos: a")
    commands.hito(session, me, "kairos: b")
    first = session.scalars(select(Milestone).order_by(Milestone.id)).first()

    reply = commands.hecho(session, me, str(first.id))

    assert session.get(Milestone, first.id).done
    assert "50% (1/2)" in reply


def test_hecho_suggests_terminar_when_progress_reaches_100(session, me):
    project = make_project(session, me)
    commands.hito(session, me, "kairos: a")
    milestone = session.scalar(select(Milestone))

    reply = commands.hecho(session, me, str(milestone.id))

    assert "100% (1/1)" in reply
    assert messages.all_milestones_done("kairos") in reply
    assert "/terminar kairos" in reply
    session.refresh(project)
    assert project.status is ProjectStatus.IDEA


def test_hecho_below_100_has_no_suggestion(session, me):
    make_project(session, me)
    commands.hito(session, me, "kairos: a")
    commands.hito(session, me, "kairos: b")
    first = session.scalars(select(Milestone).order_by(Milestone.id)).first()

    assert "/terminar" not in commands.hecho(session, me, str(first.id))


def test_hecho_on_a_done_project_has_no_suggestion(session, me):
    make_project(session, me)
    commands.hito(session, me, "kairos: a")
    milestone = session.scalar(select(Milestone))
    commands.terminar(session, me, "kairos")

    assert "/terminar" not in commands.hecho(session, me, str(milestone.id))


def test_hecho_unknown_milestone(session, me):
    assert commands.hecho(session, me, "999") == messages.error_message(MilestoneNotFound())


def test_hecho_of_another_users_milestone_is_not_found_and_untouched(session, me, users):
    other = users[1].id
    make_project(session, other, "Ajeno")
    commands.hito(session, other, "ajeno: secreto")
    milestone = session.scalar(select(Milestone))

    reply = commands.hecho(session, me, str(milestone.id))

    assert reply == messages.error_message(MilestoneNotFound())
    assert not session.get(Milestone, milestone.id).done


def test_hecho_bad_id_shows_usage(session, me):
    assert commands.hecho(session, me, "abc") == messages.USAGE["hecho"]


def test_foco_activates_and_sets_next_action_in_one_step(session, me):
    project = make_project(session, me)

    reply = commands.foco(session, me, "kairos: escribir tests")

    session.refresh(project)
    assert project.status is ProjectStatus.ACTIVE
    assert project.next_action == "escribir tests"
    assert "escribir tests" in reply


def test_foco_rejected_at_the_active_limit(session, me):
    for name in ("A", "B", "C"):
        make_project(session, me, name)
    commands.foco(session, me, "a: x")
    commands.foco(session, me, "b: x")

    reply = commands.foco(session, me, "c: x")

    assert reply == messages.error_message(ActiveLimitReached(2))
    assert "2" in reply
    assert session.scalar(select(Project).where(Project.slug == "c")).status is ProjectStatus.IDEA


def test_foco_unknown_slug(session, me):
    assert commands.foco(session, me, "nope: x") == messages.error_message(ProjectNotFound())


def test_foco_without_next_action_shows_usage(session, me):
    make_project(session, me)

    assert commands.foco(session, me, "kairos") == messages.USAGE["foco"]
    assert commands.foco(session, me, "kairos:  ") == messages.USAGE["foco"]


def test_ayuda_lists_every_command_without_emojis(session, me):
    reply = commands.ayuda(session, me, "")

    for command in ("proyecto", "idea", "hito", "hecho", "estado", "foco", "decision", "pausa", "terminar", "exportar"):
        assert f"/{command}" in reply
    assert all(ord(char) < 0x2000 for char in reply)


def test_pausa_pauses_and_keeps_next_action(session, me):
    project = make_project(session, me)
    commands.foco(session, me, "kairos: escribir tests")

    reply = commands.pausa(session, me, "kairos")

    session.refresh(project)
    assert project.status is ProjectStatus.PAUSED
    assert project.next_action == "escribir tests"
    assert "pausa" in reply


def test_pausa_frees_an_active_slot(session, me):
    for name in ("A", "B", "C"):
        make_project(session, me, name)
    commands.foco(session, me, "a: x")
    commands.foco(session, me, "b: x")

    commands.pausa(session, me, "a")

    assert "activo" in commands.foco(session, me, "c: x")


def test_pausa_unknown_slug(session, me):
    assert commands.pausa(session, me, "nope") == messages.error_message(ProjectNotFound())


def test_pausa_without_slug_shows_usage(session, me):
    assert commands.pausa(session, me, " ") == messages.USAGE["pausa"]


def test_terminar_marks_the_project_done(session, me):
    project = make_project(session, me)
    commands.foco(session, me, "kairos: x")

    reply = commands.terminar(session, me, "kairos")

    session.refresh(project)
    assert project.status is ProjectStatus.DONE
    assert "terminado" in reply


def test_terminar_unknown_slug(session, me):
    assert commands.terminar(session, me, "nope") == messages.error_message(ProjectNotFound())


def test_terminar_without_slug_shows_usage(session, me):
    assert commands.terminar(session, me, "") == messages.USAGE["terminar"]


def test_decision_records_title_and_rationale(session, me):
    make_project(session, me)

    commands.decision(session, me, "kairos: Usar SQLite | es local y simple")

    decision = session.scalar(select(Decision))
    assert (decision.title, decision.rationale) == ("Usar SQLite", "es local y simple")


@pytest.mark.parametrize("args", ["kairos: sin porque", "kairos: | solo porque", "nada"])
def test_decision_bad_format_shows_usage(session, me, args):
    make_project(session, me)

    assert commands.decision(session, me, args) == messages.USAGE["decision"]
    assert session.scalar(select(Decision)) is None


def test_decision_unknown_slug(session, me):
    assert commands.decision(session, me, "nope: t | r") == messages.error_message(
        ProjectNotFound()
    )


def test_estado_without_projects(session, me):
    assert commands.estado(session, me, "") == messages.NO_PROJECTS


def test_estado_lists_projects_with_status_progress_days_and_next_action(session, me):
    make_project(session, me, "Alpha")
    make_project(session, me, "Beta")
    commands.hito(session, me, "alpha: a")
    commands.hecho(session, me, str(session.scalar(select(Milestone)).id))
    commands.foco(session, me, "alpha: publicar")

    reply = commands.estado(session, me, "")

    assert "Alpha [alpha] - activo, 100% (1/1), tocado hoy" in reply
    assert "Próxima: publicar" in reply
    assert "Beta [beta] - idea, 0% (0/0)" in reply


def test_estado_with_slug_shows_milestones_with_ids(session, me):
    make_project(session, me)
    commands.hito(session, me, "kairos: uno")
    commands.hito(session, me, "kairos: dos")
    first, second = session.scalars(select(Milestone).order_by(Milestone.id))
    commands.hecho(session, me, str(first.id))

    reply = commands.estado(session, me, "Kairos")

    assert f"[x] #{first.id} uno" in reply
    assert f"[ ] #{second.id} dos" in reply


def test_estado_unknown_slug(session, me):
    assert commands.estado(session, me, "nope") == messages.error_message(ProjectNotFound())


def test_estado_only_shows_my_projects(session, me, users):
    make_project(session, users[1].id, "Ajeno")

    assert commands.estado(session, me, "") == messages.NO_PROJECTS


def test_replies_are_truncated_to_the_telegram_limit(session, me):
    for i in range(80):
        make_project(session, me, f"Proyecto largo numero {i}")
        commands.hito(session, me, f"proyecto-largo-numero-{i}: {'x' * 100}")

    reply = commands.estado(session, me, "proyecto-largo-numero-0")
    assert len(reply) < commands.MAX_MESSAGE_LENGTH

    reply = commands.estado(session, me, "")
    assert len(reply) == commands.MAX_MESSAGE_LENGTH
    assert reply.endswith("…")


def test_pending_milestones_lists_only_unfinished_ones(session, me):
    make_project(session, me)
    commands.hito(session, me, "kairos: uno")
    commands.hito(session, me, "kairos: dos")
    first = session.scalars(select(Milestone).order_by(Milestone.id)).first()
    commands.hecho(session, me, str(first.id))

    pending = commands.pending_milestones(session, me)

    assert [label for _, label in pending] == ["kairos: dos"]


@pytest.fixture
def vault(tmp_path, monkeypatch):
    root = tmp_path / "vault"
    root.mkdir()
    monkeypatch.setattr(
        commands, "get_settings", lambda: Settings(max_active_projects=2, obsidian_vault_path=str(root))
    )
    return root


def test_exportar_writes_the_vault_and_summarises_in_spanish(session, me, vault):
    make_project(session, me)

    reply = commands.exportar(session, me, "")

    assert reply == "Export listo: 1 proyecto, 5 archivos escritos, 0 sin cambios."
    assert (vault / "Kairos" / "kairos" / "README.md").is_file()


def test_exportar_twice_reports_no_changes(session, me, vault):
    make_project(session, me)
    commands.exportar(session, me, "")

    assert commands.exportar(session, me, "") == "Export listo: 1 proyecto, 0 archivos escritos, 5 sin cambios."


def test_exportar_lists_orphan_folders(session, me, vault):
    (vault / "Kairos" / "viejo").mkdir(parents=True)

    reply = commands.exportar(session, me, "")

    assert "0 proyectos" in reply
    assert "Carpetas huérfanas (no se tocaron): viejo" in reply


def test_exportar_only_exports_the_users_projects(session, users, vault):
    make_project(session, users[1].id, "Ajeno")

    commands.exportar(session, users[0].id, "")

    assert not (vault / "Kairos" / "ajeno").exists()


def test_exportar_without_a_vault_explains_how_to_configure_it(session, me):
    assert "OBSIDIAN_VAULT_PATH" in commands.exportar(session, me, "")
