import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

import app.models  # noqa: F401  (registers tables on Base.metadata)
from app.db import Base
from app.models import Decision, Idea, Milestone, Project, ProjectStatus, User


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


def make_project(user: User, slug: str = "kairos") -> Project:
    return Project(name="Kairos", slug=slug, user_id=user.id)


def test_project_defaults_and_utc_timestamps(session, user):
    project = make_project(user)
    session.add(project)
    session.commit()
    session.refresh(project)

    assert project.status is ProjectStatus.IDEA
    assert project.next_action is None
    assert project.created_at.utcoffset().total_seconds() == 0
    assert project.last_activity_at.tzinfo is not None


def test_project_with_children(session, user):
    project = make_project(user)
    project.milestones = [Milestone(title="B", position=1), Milestone(title="A", position=0)]
    project.ideas = [Idea(content="idea", user_id=user.id)]
    project.decisions = [Decision(title="SQLite", rationale="local first")]
    session.add(project)
    session.commit()
    session.refresh(project)

    assert [m.title for m in project.milestones] == ["A", "B"]
    assert len(project.ideas) == 1
    assert project.decisions[0].rationale == "local first"


def test_deleting_project_cascades_and_orphans_ideas(session, user):
    project = make_project(user)
    project.milestones = [Milestone(title="m")]
    project.decisions = [Decision(title="d", rationale="r")]
    project.ideas = [Idea(content="i", user_id=user.id)]
    session.add(project)
    session.commit()

    session.delete(project)
    session.commit()

    assert session.scalars(select(Milestone)).all() == []
    assert session.scalars(select(Decision)).all() == []
    ideas = session.scalars(select(Idea)).all()
    assert len(ideas) == 1
    assert ideas[0].project_id is None
    assert ideas[0].user_id == user.id


def test_idea_can_live_in_inbox(session, user):
    session.add(Idea(content="loose thought", user_id=user.id))
    session.commit()

    assert session.scalars(select(Idea)).one().project_id is None


def test_slug_is_unique(session, user):
    session.add(make_project(user, "same"))
    session.commit()
    session.add(make_project(user, "same"))

    with pytest.raises(IntegrityError):
        session.commit()


def test_foreign_keys_are_enforced(session):
    session.add(Milestone(title="orphan", project_id=999))

    with pytest.raises(IntegrityError):
        session.commit()
