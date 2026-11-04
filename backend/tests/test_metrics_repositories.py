from datetime import UTC, datetime, timedelta

import pytest

from app.models import Idea, Milestone, Project, ProjectStatus
from app.repositories.idea_repository import IdeaRepository, IdeaTotals
from app.repositories.milestone_repository import MilestoneRepository
from app.repositories.project_repository import ProjectRepository

NOW = datetime(2026, 11, 4, 12, tzinfo=UTC)
SINCE = NOW - timedelta(days=14)


def make_project(session, user, slug, status=ProjectStatus.IDEA):
    project = Project(user_id=user.id, name=slug, slug=slug, description="", status=status)
    session.add(project)
    session.flush()
    return project


def make_milestone(session, project, done=False, completed_at=None):
    session.add(
        Milestone(project_id=project.id, title="m", done=done, completed_at=completed_at)
    )
    session.flush()


def make_idea(session, user, project=None, created_at=NOW, assigned_at=None):
    session.add(
        Idea(
            user_id=user.id,
            project_id=project.id if project else None,
            content="x",
            created_at=created_at,
            assigned_at=assigned_at,
        )
    )
    session.flush()


@pytest.fixture
def user(users):
    return users[0]


@pytest.fixture
def other(users):
    return users[1]


def test_count_by_status_groups_and_omits_empty_statuses(session, user, other):
    make_project(session, user, "a", ProjectStatus.ACTIVE)
    make_project(session, user, "b", ProjectStatus.ACTIVE)
    make_project(session, user, "c", ProjectStatus.DONE)
    make_project(session, other, "d", ProjectStatus.PAUSED)

    counts = ProjectRepository(session).count_by_status(user.id)

    assert counts == {ProjectStatus.ACTIVE: 2, ProjectStatus.DONE: 1}


def test_completion_times_returns_done_milestones_inside_the_window(session, user, other):
    project = make_project(session, user, "a")
    foreign = make_project(session, other, "b")
    inside = NOW - timedelta(days=3)
    make_milestone(session, project, done=True, completed_at=inside)
    make_milestone(session, project, done=True, completed_at=NOW - timedelta(days=30))
    make_milestone(session, project, done=False)
    # A reopened milestone keeps no completion date and must not count
    make_milestone(session, project, done=False, completed_at=inside)
    make_milestone(session, foreign, done=True, completed_at=inside)

    assert MilestoneRepository(session).completion_times(user.id, SINCE) == [inside]
    assert MilestoneRepository(session).completion_times(other.id, SINCE) == [inside]


def test_created_times_filters_by_window_and_user(session, user, other):
    recent = NOW - timedelta(days=1)
    make_idea(session, user, created_at=recent)
    make_idea(session, user, created_at=NOW - timedelta(days=40))
    make_idea(session, other, created_at=recent)

    assert IdeaRepository(session).created_times(user.id, SINCE) == [recent]


def test_assigned_times_requires_a_project_and_ignores_other_users(session, user, other):
    project = make_project(session, user, "a")
    foreign = make_project(session, other, "b")
    stamp = NOW - timedelta(days=2)
    make_idea(session, user, project, assigned_at=stamp)
    # Stale assigned_at on an idea whose project was deleted (project_id NULL)
    make_idea(session, user, None, assigned_at=stamp)
    make_idea(session, user, project, assigned_at=NOW - timedelta(days=40))
    make_idea(session, other, foreign, assigned_at=stamp)

    assert IdeaRepository(session).assigned_times(user.id, SINCE) == [stamp]


def test_totals_split_inbox_and_assigned(session, user, other):
    project = make_project(session, user, "a")
    foreign = make_project(session, other, "b")
    make_idea(session, user)
    make_idea(session, user)
    make_idea(session, user, project, assigned_at=NOW)
    make_idea(session, other, foreign, assigned_at=NOW)

    repo = IdeaRepository(session)

    assert repo.totals(user.id) == IdeaTotals(captured=3, in_inbox=2, assigned=1)
    assert repo.totals(other.id) == IdeaTotals(captured=1, in_inbox=0, assigned=1)


def test_totals_of_an_empty_user_are_zero(session, user):
    assert IdeaRepository(session).totals(user.id) == IdeaTotals(0, 0, 0)
