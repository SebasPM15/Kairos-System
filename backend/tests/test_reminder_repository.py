from datetime import UTC, date, datetime

import pytest

from app.models import Project, ProjectReminderPrefs, ReminderKind
from app.repositories.reminder_repository import ReminderRepository

NOW = datetime(2026, 11, 5, 12, 0, tzinfo=UTC)
TODAY = date(2026, 11, 5)


@pytest.fixture
def projects(session, users):
    rows = [
        Project(user_id=users[0].id, name="Mine", slug="mine"),
        Project(user_id=users[0].id, name="Other mine", slug="other-mine"),
        Project(user_id=users[1].id, name="Theirs", slug="theirs"),
    ]
    session.add_all(rows)
    session.commit()
    return rows


@pytest.fixture
def repo(session):
    return ReminderRepository(session)


def test_prefs_are_found_only_by_their_owner(repo, users, projects):
    repo.add_prefs(ProjectReminderPrefs(project_id=projects[0].id, user_id=users[0].id, muted=True))

    assert repo.get_prefs(users[0].id, projects[0].id).muted is True
    assert repo.get_prefs(users[1].id, projects[0].id) is None
    assert repo.get_prefs(users[0].id, projects[1].id) is None


def test_list_prefs_returns_only_the_users_rows(repo, users, projects):
    repo.add_prefs(ProjectReminderPrefs(project_id=projects[0].id, user_id=users[0].id, muted=True))
    repo.add_prefs(ProjectReminderPrefs(project_id=projects[2].id, user_id=users[1].id, snoozed_until=NOW))

    assert [p.project_id for p in repo.list_prefs(users[0].id)] == [projects[0].id]
    assert [p.project_id for p in repo.list_prefs(users[1].id)] == [projects[2].id]


def test_list_logs_filters_by_user_and_projects_in_chronological_order(repo, users, projects):
    later = datetime(2026, 11, 6, tzinfo=UTC)
    repo.add_log(users[0].id, projects[0].id, ReminderKind.STALLED, later, date(2026, 11, 6))
    repo.add_log(users[0].id, projects[0].id, ReminderKind.STALLED, NOW, TODAY)
    repo.add_log(users[0].id, projects[1].id, ReminderKind.STALLED, NOW, TODAY)
    repo.add_log(users[1].id, projects[2].id, ReminderKind.STALLED, NOW, TODAY)

    logs = repo.list_logs(users[0].id, [projects[0].id])

    assert [log.sent_at for log in logs] == [NOW, later]
    assert repo.list_logs(users[0].id, [projects[2].id]) == []
    assert repo.list_logs(users[0].id, []) == []


def test_has_log_on_is_per_user_and_per_day(repo, users, projects):
    repo.add_log(users[0].id, projects[0].id, ReminderKind.STALLED, NOW, TODAY)

    assert repo.has_log_on(users[0].id, TODAY) is True
    assert repo.has_log_on(users[0].id, date(2026, 11, 4)) is False
    assert repo.has_log_on(users[1].id, TODAY) is False


def test_add_log_returns_the_stored_row(repo, users, projects):
    log = repo.add_log(users[0].id, projects[0].id, ReminderKind.READY_TO_FINISH, NOW, TODAY)

    assert (log.id, log.kind, log.sent_at, log.local_date) == (1, ReminderKind.READY_TO_FINISH, NOW, TODAY)
