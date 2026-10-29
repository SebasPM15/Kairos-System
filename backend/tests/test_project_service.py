from datetime import timedelta

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

import app.models  # noqa: F401  (registers tables on Base.metadata)
from app.config import Settings
from app.db import Base
from app.models import Idea, Project, ProjectStatus, User
from app.models.base import utcnow
from app.schemas.project import ProjectCreate, ProjectUpdate
from app.services.errors import ActiveLimitReached, NextActionRequired, ProjectNotFound
from app.services.project_service import ProjectService, slugify


@pytest.fixture
def session(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'test.db'}")
    Base.metadata.create_all(engine)
    with Session(engine) as s:
        yield s
    engine.dispose()


@pytest.fixture
def user(session):
    user = User()
    session.add(user)
    session.commit()
    return user


@pytest.fixture
def service(session, user):
    return ProjectService(session, user.id, Settings(max_active_projects=2))


def activate(service, project_id, next_action="do it"):
    return service.update(project_id, ProjectUpdate(status="active", next_action=next_action))


def test_create_starts_as_idea_with_slug(service):
    project = service.create(ProjectCreate(name="Mi Proyecto Ñandú"))

    assert project.status is ProjectStatus.IDEA
    assert project.slug == "mi-proyecto-nandu"
    assert project.next_action is None


def test_slugify_fallback_for_symbols():
    assert slugify("¡¿?!") == "project"


def test_duplicate_names_get_numeric_suffix(service):
    slugs = [service.create(ProjectCreate(name="Kairos")).slug for _ in range(3)]

    assert slugs == ["kairos", "kairos-2", "kairos-3"]


def test_slug_does_not_change_on_rename(service):
    project = service.create(ProjectCreate(name="Old"))

    renamed = service.update(project.id, ProjectUpdate(name="New"))

    assert renamed.name == "New"
    assert renamed.slug == "old"


def test_activate_requires_next_action(service):
    project = service.create(ProjectCreate(name="A"))

    for blank in (None, "", "   "):
        with pytest.raises(NextActionRequired):
            activate(service, project.id, blank)
    assert service.get(project.id).status is ProjectStatus.IDEA


def test_activate_uses_existing_next_action(service):
    project = service.create(ProjectCreate(name="A"))
    service.update(project.id, ProjectUpdate(next_action="write tests"))

    activated = service.update(project.id, ProjectUpdate(status="active"))

    assert activated.status is ProjectStatus.ACTIVE


def test_cannot_clear_next_action_of_active_project(service):
    project = activate(service, service.create(ProjectCreate(name="A")).id)

    with pytest.raises(NextActionRequired):
        service.update(project.id, ProjectUpdate(next_action=None))


def test_active_limit_reached(service):
    ids = [service.create(ProjectCreate(name=n)).id for n in "ABC"]
    activate(service, ids[0])
    activate(service, ids[1])

    with pytest.raises(ActiveLimitReached):
        activate(service, ids[2])


def test_reactivating_active_project_with_full_limit_is_allowed(service):
    ids = [service.create(ProjectCreate(name=n)).id for n in "AB"]
    for project_id in ids:
        activate(service, project_id)

    updated = activate(service, ids[0], "new action")

    assert updated.status is ProjectStatus.ACTIVE
    assert updated.next_action == "new action"


def test_pausing_keeps_next_action_and_frees_a_slot(service):
    ids = [service.create(ProjectCreate(name=n)).id for n in "ABC"]
    activate(service, ids[0], "keep me")
    activate(service, ids[1])

    paused = service.update(ids[0], ProjectUpdate(status="paused"))
    activate(service, ids[2])

    assert paused.status is ProjectStatus.PAUSED
    assert paused.next_action == "keep me"


def test_update_refreshes_last_activity(service):
    project = service.create(ProjectCreate(name="A"))
    project.last_activity_at = utcnow() - timedelta(days=5)

    updated = service.update(project.id, ProjectUpdate(description="x"))

    assert utcnow() - updated.last_activity_at < timedelta(minutes=1)


def test_get_missing_raises(service):
    with pytest.raises(ProjectNotFound):
        service.get(999)


def test_delete_orphans_ideas(service, session):
    project = service.create(ProjectCreate(name="A"))
    owner_id = session.get(Project, project.id).user_id
    session.add(Idea(project_id=project.id, user_id=owner_id, content="i"))
    session.commit()

    service.delete(project.id)

    assert session.scalars(select(Project)).all() == []
    idea = session.scalars(select(Idea)).one()
    assert idea.project_id is None
    assert idea.user_id == owner_id


def test_users_are_isolated(session, service):
    other = User(telegram_id=2)
    session.add(other)
    session.commit()
    other_service = ProjectService(session, other.id, Settings(max_active_projects=2))
    mine = service.create(ProjectCreate(name="Same"))

    theirs = other_service.create(ProjectCreate(name="Same"))

    assert theirs.slug == "same"  # no suffix: slugs are scoped per user
    assert [p.id for p in other_service.list()] == [theirs.id]
    with pytest.raises(ProjectNotFound):
        other_service.get(mine.id)
    with pytest.raises(ProjectNotFound):
        other_service.delete(mine.id)


def test_active_limit_is_per_user(session, service):
    other = User(telegram_id=2)
    session.add(other)
    session.commit()
    other_service = ProjectService(session, other.id, Settings(max_active_projects=2))
    for name in "AB":
        activate(service, service.create(ProjectCreate(name=name)).id)

    activated = activate(other_service, other_service.create(ProjectCreate(name="C")).id)

    assert activated.status is ProjectStatus.ACTIVE
