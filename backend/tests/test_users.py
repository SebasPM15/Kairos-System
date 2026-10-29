import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

import app.models  # noqa: F401  (registers tables on Base.metadata)
from app import deps
from app.db import Base
from app.models import Decision, Milestone, Project, User


@pytest.fixture
def session(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'test.db'}")
    Base.metadata.create_all(engine)
    with Session(engine) as s:
        yield s
    engine.dispose()


def test_user_defaults(session):
    user = User(telegram_id=5_000_000_000)
    session.add(user)
    session.commit()
    session.refresh(user)

    assert user.telegram_id == 5_000_000_000
    assert user.created_at.utcoffset().total_seconds() == 0


def test_telegram_id_is_unique_but_null_repeats(session):
    session.add_all([User(), User()])
    session.commit()

    session.add_all([User(telegram_id=1), User(telegram_id=1)])
    with pytest.raises(IntegrityError):
        session.commit()


def test_same_slug_allowed_for_different_users_only(session):
    a, b = User(), User()
    session.add_all([a, b])
    session.commit()
    session.add_all([Project(name="X", slug="x", user_id=a.id), Project(name="X", slug="x", user_id=b.id)])
    session.commit()

    session.add(Project(name="X", slug="x", user_id=a.id))
    with pytest.raises(IntegrityError):
        session.commit()


def test_project_requires_user(session):
    session.add(Project(name="X", slug="x"))

    with pytest.raises(IntegrityError):
        session.commit()


def test_deleting_user_cascades_to_projects_and_children(session):
    user = User()
    project = Project(name="X", slug="x")
    project.milestones = [Milestone(title="m")]
    project.decisions = [Decision(title="d", rationale="r")]
    user.projects = [project]
    session.add(user)
    session.commit()

    session.delete(user)
    session.commit()

    for model in (Project, Milestone, Decision):
        assert session.scalars(select(model)).all() == []


@pytest.mark.parametrize("telegram_id", [None, 42])
def test_get_current_user_creates_once(session, monkeypatch, telegram_id):
    class FakeSettings:
        telegram_allowed_user_id = telegram_id

    monkeypatch.setattr(deps, "get_settings", lambda: FakeSettings())

    first = deps.get_current_user(session)
    second = deps.get_current_user(session)

    assert first.id == second.id
    assert first.telegram_id == telegram_id
    assert len(session.scalars(select(User)).all()) == 1
