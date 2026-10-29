from datetime import timedelta

import pytest
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

import app.models  # noqa: F401  (registers tables on Base.metadata)
from app.config import Settings
from app.db import Base
from app.models import Project, User
from app.models.base import utcnow
from app.schemas.decision import DecisionCreate
from app.schemas.project import ProjectCreate
from app.services.decision_service import DecisionService
from app.services.errors import DecisionNotFound, ProjectNotFound
from app.services.project_service import ProjectService


@pytest.fixture
def session(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'test.db'}")
    Base.metadata.create_all(engine)
    with Session(engine) as s:
        yield s
    engine.dispose()


def make_user(session, telegram_id=None):
    user = User(telegram_id=telegram_id)
    session.add(user)
    session.commit()
    return user


@pytest.fixture
def user(session):
    return make_user(session)


@pytest.fixture
def other_user(session):
    return make_user(session, telegram_id=2)


@pytest.fixture
def decisions(session, user):
    return DecisionService(session, user.id)


@pytest.fixture
def project(session, user):
    created = ProjectService(session, user.id, Settings()).create(ProjectCreate(name="A"))
    # The ORM entity: tests mutate last_activity_at directly
    return session.get(Project, created.id)


@pytest.fixture
def other_project(session, other_user):
    return ProjectService(session, other_user.id, Settings()).create(ProjectCreate(name="B"))


def test_create_and_list(decisions, project):
    decision = decisions.create(
        project.id, DecisionCreate(title=" Use SQLite ", rationale=" Local only ")
    )

    assert (decision.title, decision.rationale) == ("Use SQLite", "Local only")
    assert [d.id for d in decisions.list(project.id)] == [decision.id]


@pytest.mark.parametrize(
    "payload",
    [
        {"title": "x", "rationale": ""},
        {"title": "x", "rationale": "   "},
        {"title": "", "rationale": "y"},
        {"title": "x"},
    ],
)
def test_schema_rejects_empty_fields(payload):
    with pytest.raises(ValidationError):
        DecisionCreate.model_validate(payload)


def test_create_updates_last_activity(decisions, project):
    project.last_activity_at = utcnow() - timedelta(days=5)

    decisions.create(project.id, DecisionCreate(title="t", rationale="r"))

    assert utcnow() - project.last_activity_at < timedelta(minutes=1)


def test_delete_does_not_touch_last_activity(decisions, project):
    decision = decisions.create(project.id, DecisionCreate(title="t", rationale="r"))
    project.last_activity_at = utcnow() - timedelta(days=5)

    decisions.delete(decision.id)

    assert utcnow() - project.last_activity_at > timedelta(days=4)
    assert decisions.list(project.id) == []


def test_unknown_project_and_decision(decisions):
    with pytest.raises(ProjectNotFound):
        decisions.create(999, DecisionCreate(title="t", rationale="r"))
    with pytest.raises(ProjectNotFound):
        decisions.list(999)
    with pytest.raises(DecisionNotFound):
        decisions.delete(999)


def test_isolation_between_users(session, decisions, other_user, project, other_project):
    decision = decisions.create(project.id, DecisionCreate(title="t", rationale="r"))
    theirs = DecisionService(session, other_user.id)

    with pytest.raises(ProjectNotFound):
        theirs.list(project.id)
    with pytest.raises(ProjectNotFound):
        theirs.create(project.id, DecisionCreate(title="x", rationale="y"))
    with pytest.raises(DecisionNotFound):
        theirs.delete(decision.id)
    assert theirs.list(other_project.id) == []
    assert len(decisions.list(project.id)) == 1
