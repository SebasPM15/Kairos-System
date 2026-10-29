from datetime import timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

import app.models  # noqa: F401  (registers tables on Base.metadata)
from app.config import Settings
from app.db import Base
from app.models import User
from app.models.base import utcnow
from app.schemas.milestone import MilestoneCreate, MilestoneUpdate
from app.schemas.project import ProjectCreate
from app.services.errors import MilestoneNotFound, ProjectNotFound
from app.services.milestone_service import MilestoneService, calculate_progress
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
def projects(session, user):
    return ProjectService(session, user.id, Settings())


@pytest.fixture
def milestones(session, user):
    return MilestoneService(session, user.id)


@pytest.fixture
def project(projects):
    return projects.create(ProjectCreate(name="A"))


def add(milestones, project, *titles):
    return [milestones.create(project.id, MilestoneCreate(title=t)) for t in titles]


def titles(milestones, project):
    return [m.title for m in milestones.list(project.id)]


def age(project):
    project.last_activity_at = utcnow() - timedelta(days=5)


def touched(project):
    return utcnow() - project.last_activity_at < timedelta(minutes=1)


def test_calculate_progress_floors_and_handles_empty():
    assert calculate_progress(0, 0) == 0
    assert calculate_progress(1, 3) == 33
    assert calculate_progress(2, 3) == 66
    assert calculate_progress(3, 3) == 100


def test_progress_without_milestones_is_zero(projects, project):
    current = projects.get(project.id)

    assert (current.progress, current.milestones_done, current.milestones_total) == (0, 0, 0)


def test_progress_partial_and_complete(projects, milestones, project):
    first, second = add(milestones, project, "a", "b")

    def snapshot():
        current = projects.get(project.id)
        return current.progress, current.milestones_done, current.milestones_total

    milestones.update(first.id, MilestoneUpdate(done=True))
    partial = snapshot()
    milestones.update(second.id, MilestoneUpdate(done=True))
    complete = snapshot()

    assert partial == (50, 1, 2)
    assert complete == (100, 2, 2)
    assert [p.progress for p in projects.list()] == [100]


def test_deleting_milestone_recalculates_progress(projects, milestones, project):
    done, pending = add(milestones, project, "a", "b")
    milestones.update(done.id, MilestoneUpdate(done=True))
    assert projects.get(project.id).progress == 50

    milestones.delete(pending.id)
    assert projects.get(project.id).progress == 100

    milestones.delete(done.id)
    assert projects.get(project.id).progress == 0


def test_create_appends_at_the_end(milestones, project):
    created = add(milestones, project, "a", "b", "c")

    assert [m.position for m in created] == [0, 1, 2]
    assert titles(milestones, project) == ["a", "b", "c"]


def test_completed_at_is_set_on_done_and_cleared_on_reopen(milestones, project):
    (milestone,) = add(milestones, project, "a")

    done = milestones.update(milestone.id, MilestoneUpdate(done=True))
    assert done.done and utcnow() - done.completed_at < timedelta(minutes=1)
    assert done.completed_at.utcoffset() == timedelta(0)

    reopened = milestones.update(milestone.id, MilestoneUpdate(done=False))
    assert not reopened.done and reopened.completed_at is None


def test_repeating_done_keeps_original_completed_at(milestones, project):
    (milestone,) = add(milestones, project, "a")
    first = milestones.update(milestone.id, MilestoneUpdate(done=True)).completed_at

    again = milestones.update(milestone.id, MilestoneUpdate(done=True)).completed_at

    assert again == first


def test_reorder_moves_without_gaps_or_duplicates(milestones, project):
    a, b, c, d = add(milestones, project, "a", "b", "c", "d")

    milestones.update(d.id, MilestoneUpdate(position=0))
    assert titles(milestones, project) == ["d", "a", "b", "c"]

    milestones.update(d.id, MilestoneUpdate(position=2))
    assert titles(milestones, project) == ["a", "b", "d", "c"]

    milestones.update(a.id, MilestoneUpdate(position=99))  # clamped to the end
    assert titles(milestones, project) == ["b", "d", "c", "a"]
    assert [m.position for m in milestones.list(project.id)] == [0, 1, 2, 3]


def test_delete_closes_position_gaps(milestones, project):
    _, middle, _ = add(milestones, project, "a", "b", "c")

    milestones.delete(middle.id)

    assert titles(milestones, project) == ["a", "c"]
    assert [m.position for m in milestones.list(project.id)] == [0, 1]


def test_create_complete_and_reopen_touch_project_activity(projects, milestones, project):
    stale = projects.get(project.id)

    age(stale)
    (milestone,) = add(milestones, project, "a")
    assert touched(stale)

    age(stale)
    milestones.update(milestone.id, MilestoneUpdate(done=True))
    assert touched(stale)

    age(stale)
    milestones.update(milestone.id, MilestoneUpdate(done=False))
    assert touched(stale)


def test_edit_title_reorder_and_delete_do_not_touch_activity(projects, milestones, project):
    first, second = add(milestones, project, "a", "b")
    stale = projects.get(project.id)
    age(stale)

    milestones.update(first.id, MilestoneUpdate(title="renamed"))
    milestones.update(second.id, MilestoneUpdate(position=0))
    milestones.delete(first.id)

    assert not touched(stale)


def test_title_is_stripped_and_null_fields_mean_unchanged(milestones, project):
    (milestone,) = add(milestones, project, "  padded  ")
    assert milestone.title == "padded"

    unchanged = milestones.update(
        milestone.id, MilestoneUpdate(title=None, done=None, position=None)
    )

    assert (unchanged.title, unchanged.done, unchanged.position) == ("padded", False, 0)


def test_missing_milestone_and_project_raise(milestones, project):
    with pytest.raises(MilestoneNotFound):
        milestones.update(999, MilestoneUpdate(done=True))
    with pytest.raises(MilestoneNotFound):
        milestones.delete(999)
    with pytest.raises(ProjectNotFound):
        milestones.list(999)
    with pytest.raises(ProjectNotFound):
        milestones.create(999, MilestoneCreate(title="x"))


def test_users_are_isolated(session, milestones, project):
    (mine,) = add(milestones, project, "a")
    other = MilestoneService(session, make_user(session, telegram_id=2).id)

    with pytest.raises(ProjectNotFound):
        other.list(project.id)
    with pytest.raises(ProjectNotFound):
        other.create(project.id, MilestoneCreate(title="x"))
    with pytest.raises(MilestoneNotFound):
        other.update(mine.id, MilestoneUpdate(done=True))
    with pytest.raises(MilestoneNotFound):
        other.delete(mine.id)
    assert titles(milestones, project) == ["a"]
