from datetime import timedelta

import pytest
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

import app.models  # noqa: F401  (registers tables on Base.metadata)
from app.config import Settings
from app.db import Base
from app.models import User
from app.models.base import utcnow
from app.schemas.idea import IdeaCreate, IdeaUpdate
from app.schemas.project import ProjectCreate
from app.services.errors import IdeaNotFound, ProjectNotFound
from app.services.idea_service import IdeaService
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
def ideas(session, user):
    return IdeaService(session, user.id)


@pytest.fixture
def project(session, user):
    return ProjectService(session, user.id, Settings()).create(ProjectCreate(name="A"))


@pytest.fixture
def other_project(session, other_user):
    return ProjectService(session, other_user.id, Settings()).create(ProjectCreate(name="B"))


def age(project):
    project.last_activity_at = utcnow() - timedelta(days=5)


def touched(project):
    return utcnow() - project.last_activity_at < timedelta(minutes=1)


def test_create_in_project_and_inbox(ideas, project):
    in_project = ideas.create(IdeaCreate(content="  a  ", project_id=project.id))
    in_inbox = ideas.create(IdeaCreate(content="b"))

    assert (in_project.project_id, in_project.content) == (project.id, "a")
    assert in_inbox.project_id is None
    assert [i.id for i in ideas.list_by_project(project.id)] == [in_project.id]
    assert [i.id for i in ideas.list_inbox()] == [in_inbox.id]


def test_create_rejects_blank_content():
    with pytest.raises(ValidationError):
        IdeaCreate(content="   ")


def test_create_in_foreign_project_is_not_found(ideas, other_project):
    with pytest.raises(ProjectNotFound):
        ideas.create(IdeaCreate(content="x", project_id=other_project.id))


def test_list_by_missing_project_is_not_found(ideas):
    with pytest.raises(ProjectNotFound):
        ideas.list_by_project(999)


def test_assign_and_unassign(ideas, project):
    idea = ideas.create(IdeaCreate(content="x"))

    assigned = ideas.update(idea.id, IdeaUpdate(project_id=project.id))
    assert assigned.project_id == project.id

    back = ideas.update(idea.id, IdeaUpdate(project_id=None))
    assert back.project_id is None
    assert [i.id for i in ideas.list_inbox()] == [idea.id]


def test_assign_to_foreign_project_is_not_found(ideas, other_project):
    idea = ideas.create(IdeaCreate(content="x"))

    with pytest.raises(ProjectNotFound):
        ideas.update(idea.id, IdeaUpdate(project_id=other_project.id))
    assert ideas.list_inbox()[0].project_id is None


def test_patch_absent_vs_explicit_null(ideas, project):
    idea = ideas.create(IdeaCreate(content="x", project_id=project.id))

    only_content = ideas.update(idea.id, IdeaUpdate.model_validate({"content": "y"}))
    assert (only_content.content, only_content.project_id) == ("y", project.id)

    explicit_null = ideas.update(idea.id, IdeaUpdate.model_validate({"project_id": None}))
    assert (explicit_null.content, explicit_null.project_id) == ("y", None)


def test_patch_content_cannot_be_null():
    with pytest.raises(ValidationError):
        IdeaUpdate.model_validate({"content": None})


def test_update_and_delete_unknown_idea(ideas):
    with pytest.raises(IdeaNotFound):
        ideas.update(999, IdeaUpdate(content="x"))
    with pytest.raises(IdeaNotFound):
        ideas.delete(999)


def test_delete_removes_idea(ideas):
    idea = ideas.create(IdeaCreate(content="x"))

    ideas.delete(idea.id)

    assert ideas.list_inbox() == []


def test_last_activity_follows_rule(ideas, project):
    age(project)
    ideas.create(IdeaCreate(content="inbox"))
    assert not touched(project)

    in_project = ideas.create(IdeaCreate(content="x", project_id=project.id))
    assert touched(project)

    age(project)
    ideas.update(in_project.id, IdeaUpdate(content="edited"))
    assert not touched(project)

    ideas.update(in_project.id, IdeaUpdate(project_id=None))
    assert not touched(project)

    ideas.update(in_project.id, IdeaUpdate(project_id=project.id))
    assert touched(project)

    age(project)
    ideas.delete(in_project.id)
    assert not touched(project)


def test_isolation_between_users(session, ideas, other_user, project):
    mine = ideas.create(IdeaCreate(content="mine", project_id=project.id))
    inbox = ideas.create(IdeaCreate(content="inbox"))
    theirs = IdeaService(session, other_user.id)

    assert theirs.list_inbox() == []
    with pytest.raises(IdeaNotFound):
        theirs.update(mine.id, IdeaUpdate(content="hijack"))
    with pytest.raises(IdeaNotFound):
        theirs.delete(inbox.id)
    with pytest.raises(ProjectNotFound):
        theirs.list_by_project(project.id)


def test_deleting_project_returns_ideas_to_inbox(session, user, ideas, project):
    idea = ideas.create(IdeaCreate(content="x", project_id=project.id))

    ProjectService(session, user.id, Settings()).delete(project.id)
    session.expire_all()

    assert [i.id for i in ideas.list_inbox()] == [idea.id]
    assert ideas.list_inbox()[0].project_id is None
