import json
from datetime import UTC, datetime

import pytest

from app.config import Settings
from app.exporters import markdown
from app.exporters.project_exporter import build_exporter
from app.models import Project, ProjectStatus
from app.schemas.decision import DecisionCreate
from app.schemas.idea import IdeaCreate
from app.schemas.milestone import MilestoneCreate, MilestoneUpdate
from app.schemas.project import ProjectCreate, ProjectUpdate
from app.services.decision_service import DecisionService
from app.services.errors import UnsafeVaultPath, VaultNotConfigured
from app.services.idea_service import IdeaService
from app.services.milestone_service import MilestoneService
from app.services.project_service import ProjectService


@pytest.fixture
def vault(tmp_path):
    root = tmp_path / "vault"
    root.mkdir()
    return root


@pytest.fixture
def me(users):
    return users[0].id


def settings_for(vault) -> Settings:
    return Settings(obsidian_vault_path=str(vault), max_active_projects=3)


def exporter(session, user_id, vault):
    return build_exporter(session, user_id, settings_for(vault))


def make_project(session, user_id, name="Kairos", **fields):
    service = ProjectService(session, user_id, Settings(max_active_projects=3))
    project = service.create(ProjectCreate(name=name, description=fields.pop("description", "")))
    if fields:
        project = service.update(project.id, ProjectUpdate(**fields))
    return project


def read(vault, *parts):
    return vault.joinpath("Kairos", *parts).read_text(encoding="utf-8")


def snapshot(vault):
    return {
        path.relative_to(vault).as_posix(): path.read_bytes()
        for path in vault.rglob("*")
        if path.is_file()
    }


def test_exports_the_expected_file_structure(session, me, vault):
    make_project(session, me, "Kairos")
    make_project(session, me, "Otro Proyecto")

    summary = exporter(session, me, vault).export()

    assert sorted(snapshot(vault)) == [
        "Kairos/_bandeja.md",
        "Kairos/kairos/README.md",
        "Kairos/kairos/decisiones.md",
        "Kairos/kairos/hitos.md",
        "Kairos/kairos/ideas.md",
        "Kairos/otro-proyecto/README.md",
        "Kairos/otro-proyecto/decisiones.md",
        "Kairos/otro-proyecto/hitos.md",
        "Kairos/otro-proyecto/ideas.md",
    ]
    assert (summary.projects_exported, summary.files_written, summary.files_unchanged) == (2, 9, 0)
    assert summary.orphans == []


def test_file_contents_reflect_the_database(session, me, vault):
    project = make_project(session, me, "Kairos", description="Asistente personal")
    milestones = MilestoneService(session, me)
    first = milestones.create(project.id, MilestoneCreate(title="Modelos"))
    milestones.create(project.id, MilestoneCreate(title="API"))
    milestones.update(first.id, MilestoneUpdate(done=True))
    IdeaService(session, me).create(IdeaCreate(content="Usar webhooks", project_id=project.id))
    IdeaService(session, me).create(IdeaCreate(content="Idea suelta"))
    DecisionService(session, me).create(
        project.id, DecisionCreate(title="Usar SQLite", rationale="Es local y simple")
    )
    ProjectService(session, me, Settings(max_active_projects=3)).update(
        project.id, ProjectUpdate(status=ProjectStatus.ACTIVE, next_action="Escribir el export")
    )

    exporter(session, me, vault).export()

    readme = read(vault, "kairos", "README.md")
    assert readme.startswith("---\n")
    assert 'status: "active"\nprogress: 50\nmilestones_done: 1\nmilestones_total: 2\n' in readme
    assert 'next_action: "Escribir el export"\n' in readme
    assert "Asistente personal" in readme
    assert "- [x] Modelos\n- [ ] API\n" in read(vault, "kairos", "hitos.md")
    assert "Usar webhooks" in read(vault, "kairos", "ideas.md")
    assert "Idea suelta" not in read(vault, "kairos", "ideas.md")
    decisions = read(vault, "kairos", "decisiones.md")
    assert "## Usar SQLite" in decisions
    assert "Es local y simple" in decisions
    inbox = read(vault, "_bandeja.md")
    assert "Idea suelta" in inbox
    assert "Usar webhooks" not in inbox


def test_every_generated_file_carries_the_notice(session, me, vault):
    make_project(session, me)

    exporter(session, me, vault).export()

    assert all(markdown.NOTICE in content.decode() for content in snapshot(vault).values())


def test_milestones_follow_their_position(session, me, vault):
    project = make_project(session, me)
    milestones = MilestoneService(session, me)
    milestones.create(project.id, MilestoneCreate(title="Uno"))
    milestones.create(project.id, MilestoneCreate(title="Dos"))
    last = milestones.create(project.id, MilestoneCreate(title="Tres"))
    milestones.update(last.id, MilestoneUpdate(position=0))

    exporter(session, me, vault).export()

    assert "- [ ] Tres\n- [ ] Uno\n- [ ] Dos\n" in read(vault, "kairos", "hitos.md")


@pytest.mark.parametrize(
    "next_action",
    ['Hablar con: "Ana"', "a: b # c", "- guion", "linea 1\nlinea 2", "back\\slash", "ñandú: ✓", "null"],
)
def test_frontmatter_survives_awkward_next_actions(session, me, vault, next_action):
    make_project(session, me, status=ProjectStatus.ACTIVE, next_action=next_action)

    exporter(session, me, vault).export()

    frontmatter = read(vault, "kairos", "README.md").split("---\n")[1]
    lines = dict(line.split(": ", 1) for line in frontmatter.splitlines())
    assert json.loads(lines["next_action"]) == next_action
    assert set(lines) == {
        "status", "progress", "milestones_done", "milestones_total", "next_action", "last_activity",
    }


def test_second_export_writes_nothing(session, me, vault):
    project = make_project(session, me)
    IdeaService(session, me).create(IdeaCreate(content="x", project_id=project.id))
    exporter(session, me, vault).export()
    before = snapshot(vault)

    summary = exporter(session, me, vault).export()

    assert (summary.files_written, summary.files_unchanged) == (0, 5)
    assert snapshot(vault) == before


def test_only_changed_files_are_rewritten(session, me, vault):
    project = make_project(session, me)
    # Far in the past so the idea's activity timestamp visibly differs at second resolution
    session.get(Project, project.id).last_activity_at = datetime(2020, 1, 1, tzinfo=UTC)
    session.commit()
    exporter(session, me, vault).export()
    IdeaService(session, me).create(IdeaCreate(content="nueva", project_id=project.id))

    summary = exporter(session, me, vault).export()

    # ideas.md changed, and README.md because adding an idea touches last_activity_at
    assert (summary.files_written, summary.files_unchanged) == (2, 3)
    assert "nueva" in read(vault, "kairos", "ideas.md")


def test_manual_edits_are_overwritten(session, me, vault):
    make_project(session, me)
    exporter(session, me, vault).export()
    (vault / "Kairos" / "kairos" / "hitos.md").write_text("editado a mano")

    summary = exporter(session, me, vault).export()

    assert summary.files_written == 1
    assert markdown.NOTICE in read(vault, "kairos", "hitos.md")


def test_orphan_folders_are_reported_and_left_untouched(session, me, vault):
    project = make_project(session, me, "Viejo")
    exporter(session, me, vault).export()
    ProjectService(session, me, Settings()).delete(project.id)
    stray = vault / "Kairos" / "a-mano"
    stray.mkdir()
    (stray / "notas.md").write_text("mías")
    before = snapshot(vault)

    summary = exporter(session, me, vault).export()

    assert summary.orphans == ["a-mano", "viejo"]
    assert summary.projects_exported == 0
    # Nothing was deleted or modified; only the inbox file is new
    after = snapshot(vault)
    assert before.items() <= after.items()
    assert (stray / "notas.md").read_text() == "mías"


def test_folders_of_current_projects_are_not_orphans(session, me, vault):
    make_project(session, me)

    assert exporter(session, me, vault).export().orphans == []


def test_other_users_projects_are_not_exported(session, users, vault):
    mine, theirs = users[0].id, users[1].id
    make_project(session, mine, "Mio")
    other = make_project(session, theirs, "Ajeno")
    ProjectService(session, theirs, Settings()).update(other.id, ProjectUpdate(description="secreto"))
    IdeaService(session, theirs).create(IdeaCreate(content="idea ajena"))
    DecisionService(session, theirs).create(
        other.id, DecisionCreate(title="decision ajena", rationale="porque si")
    )

    summary = exporter(session, mine, vault).export()

    assert summary.projects_exported == 1
    files = snapshot(vault)
    assert not any("ajeno" in path for path in files)
    assert not any(b"secreto" in data or b"ajena" in data for data in files.values())


def test_vault_not_configured(session, me):
    with pytest.raises(VaultNotConfigured):
        build_exporter(session, me, Settings(obsidian_vault_path=""))


def test_missing_vault_root_is_not_created(session, me, tmp_path):
    missing = tmp_path / "no-existe"

    with pytest.raises(VaultNotConfigured):
        build_exporter(session, me, Settings(obsidian_vault_path=str(missing)))

    assert not missing.exists()


def test_only_kairos_is_created_inside_the_vault(session, me, vault):
    (vault / "Mis notas").mkdir()
    make_project(session, me)

    exporter(session, me, vault).export()

    assert sorted(p.name for p in vault.iterdir()) == ["Kairos", "Mis notas"]


@pytest.mark.parametrize("slug", ["../evil", "..", "a/../../evil", "/abs", ""])
def test_a_hostile_slug_cannot_escape_kairos(session, me, vault, slug):
    project = make_project(session, me)
    session.get(Project, project.id).slug = slug
    session.commit()

    with pytest.raises(UnsafeVaultPath):
        exporter(session, me, vault).export()

    assert not (vault / "evil").exists()
    assert not (vault.parent / "evil").exists()
    assert not (vault / "README.md").exists()
