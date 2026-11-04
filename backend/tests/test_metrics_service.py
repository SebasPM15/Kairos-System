from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import event

from app.config import Settings
from app.models import Idea, Milestone, ProjectStatus
from app.models.base import utcnow
from app.schemas.idea import IdeaCreate, IdeaUpdate
from app.schemas.milestone import MilestoneCreate, MilestoneUpdate
from app.schemas.project import ProjectCreate, ProjectUpdate
from app.services.idea_service import IdeaService
from app.services.metrics_service import MetricsService
from app.services.milestone_service import MilestoneService
from app.services.project_service import ProjectService

# Wednesday; the current local week starts Monday 2026-11-02
NOW = datetime(2026, 11, 4, 12, tzinfo=UTC)
SETTINGS = Settings(max_active_projects=5)


@pytest.fixture
def user(users):
    return users[0]


@pytest.fixture
def other(users):
    return users[1]


def metrics(session, user, weeks=4, now=NOW):
    return MetricsService(session, user.id, SETTINGS, clock=lambda: now).get(weeks)


def new_project(session, user, name="A", status=None):
    service = ProjectService(session, user.id, SETTINGS)
    project = service.create(ProjectCreate(name=name))
    if status is not None:
        service.update(project.id, ProjectUpdate(status=status, next_action="go"))
    return project


def counts(series):
    return [point.count for point in series]


def test_empty_user_gets_zero_filled_series_of_the_requested_length(session, user):
    result = metrics(session, user, weeks=6)

    assert result.weeks == 6
    assert result.timezone == "America/Guayaquil"
    assert str(result.current_week_start) == "2026-11-02"
    for series in (result.milestones_completed, result.ideas_captured, result.ideas_assigned):
        assert counts(series) == [0] * 6
    assert result.project_progress == []
    assert result.idea_totals.captured == 0


def test_projects_by_status_always_has_four_entries_with_zeros(session, user):
    new_project(session, user, "A")
    new_project(session, user, "B", ProjectStatus.ACTIVE)

    result = metrics(session, user)

    assert [(s.status.value, s.count) for s in result.projects_by_status] == [
        ("idea", 1),
        ("active", 1),
        ("paused", 0),
        ("done", 0),
    ]


def test_project_progress_lists_active_first_with_milestone_figures(session, user):
    idea = new_project(session, user, "Idea")
    active = new_project(session, user, "Active", ProjectStatus.ACTIVE)
    milestones = MilestoneService(session, user.id)
    first = milestones.create(active.id, MilestoneCreate(title="a"))
    milestones.create(active.id, MilestoneCreate(title="b"))
    milestones.update(first.id, MilestoneUpdate(done=True))

    progress = metrics(session, user).project_progress

    assert [p.id for p in progress] == [active.id, idea.id]
    assert (progress[0].progress, progress[0].milestones_done, progress[0].milestones_total) == (
        50,
        1,
        2,
    )
    assert progress[1].milestones_total == 0


def test_reopened_milestone_stops_counting_and_recompleting_counts_again(session, user):
    project = new_project(session, user)
    milestones = MilestoneService(session, user.id)
    milestone = milestones.create(project.id, MilestoneCreate(title="a"))
    milestones.update(milestone.id, MilestoneUpdate(done=True))
    stored = session.get(Milestone, milestone.id)
    stored.completed_at = NOW - timedelta(weeks=2)
    session.commit()
    assert counts(metrics(session, user).milestones_completed) == [0, 1, 0, 0]

    milestones.update(milestone.id, MilestoneUpdate(done=False))
    assert counts(metrics(session, user).milestones_completed) == [0, 0, 0, 0]

    milestones.update(milestone.id, MilestoneUpdate(done=True))
    stored.completed_at = NOW
    session.commit()
    assert counts(metrics(session, user).milestones_completed) == [0, 0, 0, 1]


def test_ideas_captured_and_assigned_land_in_their_own_weeks(session, user):
    project = new_project(session, user)
    service = IdeaService(session, user.id)
    inbox = service.create(IdeaCreate(content="a"))
    assigned = service.create(IdeaCreate(content="b", project_id=project.id))
    session.get(Idea, inbox.id).created_at = NOW - timedelta(weeks=3)
    stored = session.get(Idea, assigned.id)
    stored.created_at = NOW - timedelta(weeks=2)
    stored.assigned_at = NOW - timedelta(weeks=1)
    session.commit()

    result = metrics(session, user)

    assert counts(result.ideas_captured) == [1, 1, 0, 0]
    assert counts(result.ideas_assigned) == [0, 0, 1, 0]
    assert (result.idea_totals.captured, result.idea_totals.in_inbox) == (2, 1)
    assert result.idea_totals.assigned == 1


def test_ideas_of_a_deleted_project_and_returned_to_inbox_leave_the_assigned_series(
    session, user
):
    keep = new_project(session, user, "Keep")
    gone = new_project(session, user, "Gone")
    service = IdeaService(session, user.id)
    service.create(IdeaCreate(content="a", project_id=gone.id))
    returned = service.create(IdeaCreate(content="b", project_id=keep.id))
    service.create(IdeaCreate(content="c", project_id=keep.id))
    service.update(returned.id, IdeaUpdate(project_id=None))
    ProjectService(session, user.id, SETTINGS).delete(gone.id)

    # The ideas were stamped by the real clock, so the window must end at the real "now"
    result = metrics(session, user, now=utcnow())

    assert counts(result.ideas_assigned) == [0, 0, 0, 1]
    assert result.idea_totals.assigned == 1
    assert counts(result.ideas_captured) == [0, 0, 0, 3]


def test_users_do_not_see_each_others_data(session, user, other):
    project = new_project(session, other, "Theirs", ProjectStatus.ACTIVE)
    MilestoneService(session, other.id).create(project.id, MilestoneCreate(title="m"))
    IdeaService(session, other.id).create(IdeaCreate(content="x", project_id=project.id))

    result = metrics(session, user)

    assert result.project_progress == []
    assert sum(s.count for s in result.projects_by_status) == 0
    assert counts(result.ideas_captured) == [0] * 4
    assert result.idea_totals.captured == 0


def test_query_count_does_not_grow_with_the_number_of_projects(session, user):
    def count_statements() -> int:
        statements = []

        def record(conn, cursor, statement, *args):
            statements.append(statement)

        engine = session.get_bind()
        event.listen(engine, "before_cursor_execute", record)
        try:
            metrics(session, user)
        finally:
            event.remove(engine, "before_cursor_execute", record)
        return len(statements)

    new_project(session, user, "P0")
    few = count_statements()
    for index in range(1, 10):
        project = new_project(session, user, f"P{index}")
        MilestoneService(session, user.id).create(project.id, MilestoneCreate(title="m"))
        IdeaService(session, user.id).create(IdeaCreate(content="x", project_id=project.id))
    many = count_statements()

    assert few == many
