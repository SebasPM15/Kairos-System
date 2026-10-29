import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

import app.models  # noqa: F401  (registers tables on Base.metadata)
from app.db import Base
from app.models import Decision, Idea, Milestone, Project, ProjectStatus


@pytest.fixture
def session(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'test.db'}")
    Base.metadata.create_all(engine)
    with Session(engine) as s:
        yield s
    engine.dispose()


def make_project(slug: str = "kairos") -> Project:
    return Project(name="Kairos", slug=slug)


def test_project_defaults_and_utc_timestamps(session):
    project = make_project()
    session.add(project)
    session.commit()
    session.refresh(project)

    assert project.status is ProjectStatus.IDEA
    assert project.next_action is None
    assert project.created_at.utcoffset().total_seconds() == 0
    assert project.last_activity_at.tzinfo is not None


def test_project_with_children(session):
    project = make_project()
    project.milestones = [Milestone(title="B", position=1), Milestone(title="A", position=0)]
    project.ideas = [Idea(content="idea")]
    project.decisions = [Decision(title="SQLite", rationale="local first")]
    session.add(project)
    session.commit()
    session.refresh(project)

    assert [m.title for m in project.milestones] == ["A", "B"]
    assert len(project.ideas) == 1
    assert project.decisions[0].rationale == "local first"


def test_deleting_project_cascades_and_orphans_ideas(session):
    project = make_project()
    project.milestones = [Milestone(title="m")]
    project.decisions = [Decision(title="d", rationale="r")]
    project.ideas = [Idea(content="i")]
    session.add(project)
    session.commit()

    session.delete(project)
    session.commit()

    assert session.scalars(select(Milestone)).all() == []
    assert session.scalars(select(Decision)).all() == []
    ideas = session.scalars(select(Idea)).all()
    assert len(ideas) == 1
    assert ideas[0].project_id is None


def test_idea_can_live_in_inbox(session):
    session.add(Idea(content="loose thought"))
    session.commit()

    assert session.scalars(select(Idea)).one().project_id is None


def test_slug_is_unique(session):
    session.add(make_project("same"))
    session.commit()
    session.add(make_project("same"))

    with pytest.raises(IntegrityError):
        session.commit()


def test_foreign_keys_are_enforced(session):
    session.add(Milestone(title="orphan", project_id=999))

    with pytest.raises(IntegrityError):
        session.commit()
