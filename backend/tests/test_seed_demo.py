import importlib.util
from pathlib import Path

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

import app.models  # noqa: F401  (registers tables on Base.metadata)
from app.config import Settings
from app.db import Base
from app.models import Idea, Project, ProjectStatus, User
from app.schemas.project import ProjectCreate, ProjectUpdate
from app.services.errors import ActiveLimitReached
from app.services.project_service import ProjectService

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "seed_demo.py"
spec = importlib.util.spec_from_file_location("seed_demo", SCRIPT)
seed_demo = importlib.util.module_from_spec(spec)
spec.loader.exec_module(seed_demo)


@pytest.fixture
def db_url(tmp_path):
    url = f"sqlite:///{tmp_path / 'demo-test.db'}"
    engine = create_engine(url)
    Base.metadata.create_all(engine)
    engine.dispose()
    return url


@pytest.fixture
def session(db_url):
    engine = create_engine(db_url)
    with Session(engine, expire_on_commit=False) as s:
        yield s
    engine.dispose()


def seeded(session, **kwargs):
    return seed_demo.seed(session, Settings(telegram_allowed_user_id=None), **{"reset": False, **kwargs})


def test_seed_covers_every_status_with_the_right_progress(session):
    projects = {p.name: p for p in seeded(session)}

    by_status = {}
    for project in projects.values():
        by_status.setdefault(project.status, []).append(project)
    assert {s: len(v) for s, v in by_status.items()} == {
        ProjectStatus.ACTIVE: 3,
        ProjectStatus.PAUSED: 3,
        ProjectStatus.IDEA: 2,
        ProjectStatus.DONE: 1,
    }
    assert sorted(p.progress for p in by_status[ProjectStatus.ACTIVE]) == [0, 60, 80]
    assert all(p.next_action for p in by_status[ProjectStatus.ACTIVE])
    assert by_status[ProjectStatus.DONE][0].progress == 100


def test_seed_has_a_stale_project_and_long_texts(session):
    projects = seeded(session)

    assert any(p.days_since_activity > 30 for p in projects)
    assert any(p.days_since_activity <= 3 for p in projects)
    assert max(len(p.name) for p in projects) > 80
    assert max(len(p.next_action or "") for p in projects) > 150


def test_seed_creates_four_inbox_ideas_and_four_assigned(session):
    seeded(session)

    ideas = session.scalars(select(Idea)).all()
    assert len(ideas) == 8
    assert sum(1 for i in ideas if i.project_id is None) == 4


def test_seed_never_exceeds_the_active_limit_and_the_fourth_is_rejected(session):
    # An environment with a bigger limit must not change the demo scenario
    seed_demo.seed(session, Settings(telegram_allowed_user_id=None, max_active_projects=10), reset=False)
    settings = Settings(telegram_allowed_user_id=None, max_active_projects=3)
    user = session.scalar(select(User))
    service = ProjectService(session, user.id, settings)
    fourth = next(p for p in service.list() if p.status is ProjectStatus.IDEA)

    with pytest.raises(ActiveLimitReached):
        service.update(fourth.id, ProjectUpdate(status=ProjectStatus.ACTIVE, next_action="Probar"))


def test_second_run_without_reset_is_refused_and_changes_nothing(session):
    seeded(session)

    with pytest.raises(seed_demo.SeedRefused):
        seeded(session)

    assert session.scalar(select(func.count()).select_from(Project)) == 9


def test_reset_reseeds_without_duplicates_and_keeps_other_users(session):
    seeded(session)
    other = User(telegram_id=77)
    session.add(other)
    session.commit()
    ProjectService(session, other.id, Settings()).create(ProjectCreate(name="Ajeno"))

    seeded(session, reset=True)

    assert session.scalar(select(func.count()).select_from(Project).where(Project.user_id != other.id)) == 9
    assert session.scalar(select(func.count()).select_from(Idea)) == 8
    assert session.scalar(select(Project.name).where(Project.user_id == other.id)) == "Ajeno"


@pytest.mark.parametrize(
    "url",
    ["sqlite:///./kairos.db", "sqlite:////data/kairos.db", "postgresql://u:p@localhost/demo", "sqlite://"],
)
def test_real_or_unsupported_targets_are_refused(url):
    with pytest.raises(seed_demo.SeedRefused):
        seed_demo.check_target(url)


def test_demo_named_sqlite_file_is_accepted():
    seed_demo.check_target("sqlite:///./demo.db")


def test_target_url_prefers_cli_then_environment_then_default(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    assert seed_demo.target_url(None) == seed_demo.DEFAULT_DATABASE_URL
    monkeypatch.setenv("DATABASE_URL", "sqlite:///./demo-env.db")
    assert seed_demo.target_url(None) == "sqlite:///./demo-env.db"
    assert seed_demo.target_url("sqlite:///./demo-cli.db") == "sqlite:///./demo-cli.db"


def test_main_refuses_real_database_and_missing_tables(tmp_path, db_url, capsys):
    assert seed_demo.main(["--database-url", "sqlite:///./kairos.db"]) == 1
    assert "no parece una base de demo" in capsys.readouterr().err

    empty = f"sqlite:///{tmp_path / 'demo-empty.db'}"
    assert seed_demo.main(["--database-url", empty]) == 1
    assert "alembic upgrade head" in capsys.readouterr().err

    assert seed_demo.main(["--database-url", db_url]) == 0
    assert seed_demo.main(["--database-url", db_url]) == 1
    assert seed_demo.main(["--database-url", db_url, "--reset"]) == 0
