import importlib.util
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import pytest
from pydantic import ValidationError
from sqlalchemy import func, select

from app.config import Settings
from app.models import Milestone, Project, ProjectStatus, ReminderKind, ReminderLog, User
from app.schemas.reminder import ReminderPrefsUpdate
from app.services.errors import ProjectNotFound
from app.services.reminder_service import ReminderService

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "seed_demo.py"
spec = importlib.util.spec_from_file_location("seed_demo", SCRIPT)
seed_demo = importlib.util.module_from_spec(spec)
spec.loader.exec_module(seed_demo)

NOW = datetime(2026, 11, 5, 15, 0, tzinfo=UTC)


class Clock:
    def __init__(self, now: datetime = NOW) -> None:
        self.now = now

    def __call__(self) -> datetime:
        return self.now


@pytest.fixture
def clock():
    return Clock()


def service_for(session, user, clock, **overrides):
    return ReminderService(session, user.id, Settings(**overrides), clock=clock)


@pytest.fixture
def service(session, users, clock):
    return service_for(session, users[0], clock)


def add_project(session, user, name, status=ProjectStatus.ACTIVE, idle=0, done=0, total=0, next_action="go"):
    project = Project(
        user_id=user.id,
        name=name,
        slug=name.lower().replace(" ", "-"),
        status=status,
        next_action=next_action,
        last_activity_at=NOW - timedelta(days=idle),
    )
    session.add(project)
    session.flush()
    for position in range(total):
        session.add(Milestone(project_id=project.id, title=f"m{position}", done=position < done, position=position))
    session.commit()
    return project


def kinds(service):
    return {a.slug: a.kind for a in service.overview().alerts}


# --- thresholds ---------------------------------------------------------------------------


def test_demo_data_alerts_rust_as_active_and_blog_as_paused(tmp_path):
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session

    import app.models  # noqa: F401
    from app.db import Base

    engine = create_engine(f"sqlite:///{tmp_path / 'demo-test.db'}")
    Base.metadata.create_all(engine)
    with Session(engine, expire_on_commit=False) as session:
        seed_demo.seed(session, Settings(telegram_allowed_user_id=None), reset=False, history=False)
        user = session.scalar(select(User))
        clock = Clock(datetime.now(UTC))

        alerts = ReminderService(session, user.id, Settings(), clock=clock).overview().alerts
        assert [(a.name, a.status, a.kind, a.days_idle, a.threshold_days) for a in alerts] == [
            ("Blog de cocina casera", ProjectStatus.PAUSED, ReminderKind.STALLED, 47, 30),
            ("Curso de Rust", ProjectStatus.ACTIVE, ReminderKind.STALLED, 12, 7),
        ]

        looser = ReminderService(session, user.id, Settings(stale_days_active=14, stale_days_paused=14), clock=clock)
        assert {a.name for a in looser.overview().alerts} == {"Blog de cocina casera", "Huerto urbano en el balcón"}

        strict = ReminderService(session, user.id, Settings(stale_days_paused=50), clock=clock)
        assert {a.name for a in strict.overview().alerts} == {"Curso de Rust"}
    engine.dispose()


@pytest.mark.parametrize(
    ("status", "idle", "expected"),
    [
        (ProjectStatus.ACTIVE, 6, None),
        (ProjectStatus.ACTIVE, 7, ReminderKind.STALLED),
        (ProjectStatus.PAUSED, 29, None),
        (ProjectStatus.PAUSED, 30, ReminderKind.STALLED),
        (ProjectStatus.IDEA, 400, None),
        (ProjectStatus.DONE, 400, None),
    ],
)
def test_threshold_depends_on_the_status(session, users, service, status, idle, expected):
    add_project(session, users[0], "P", status=status, idle=idle, total=2)

    assert kinds(service).get("p") == expected


def test_active_project_with_every_milestone_done_is_ready_to_finish_even_when_fresh(session, users, service):
    add_project(session, users[0], "Fresh", idle=0, done=3, total=3)

    alert = service.overview().alerts[0]

    assert (alert.kind, alert.threshold_days, alert.milestones_total) == (ReminderKind.READY_TO_FINISH, None, 3)


def test_ready_to_finish_wins_over_stalled(session, users, service):
    add_project(session, users[0], "Both", idle=20, done=2, total=2)

    assert kinds(service) == {"both": ReminderKind.READY_TO_FINISH}


def test_active_project_without_milestones_is_stalled_and_says_so(session, users, service):
    add_project(session, users[0], "Bare", idle=10, total=0)

    alert = service.overview().alerts[0]

    assert (alert.kind, alert.milestones_total) == (ReminderKind.STALLED, 0)


def test_a_paused_project_at_100_percent_is_only_stalled(session, users, service):
    add_project(session, users[0], "Paused full", status=ProjectStatus.PAUSED, idle=40, done=2, total=2)

    assert kinds(service) == {"paused-full": ReminderKind.STALLED}


def test_alerts_are_ordered_from_the_longest_idle(session, users, service):
    add_project(session, users[0], "A", idle=8)
    add_project(session, users[0], "B", idle=30)
    add_project(session, users[0], "C", status=ProjectStatus.PAUSED, idle=90)

    assert [a.slug for a in service.overview().alerts] == ["c", "b", "a"]


# --- snooze and mute ----------------------------------------------------------------------


def test_snoozed_project_leaves_the_alerts_and_is_listed_until_it_expires(session, users, service, clock):
    project = add_project(session, users[0], "Rust", idle=12)

    prefs = service.update_prefs(project.id, ReminderPrefsUpdate(snooze_days=3))

    assert prefs.snoozed_until == NOW + timedelta(days=3)
    overview = service.overview()
    assert overview.alerts == []
    assert [(s.slug, s.snoozed_until, s.muted, s.kind) for s in overview.suppressed] == [
        ("rust", NOW + timedelta(days=3), False, ReminderKind.STALLED)
    ]
    clock.now = NOW + timedelta(days=3, seconds=1)
    overview = service.overview()
    assert [a.slug for a in overview.alerts] == ["rust"]
    assert overview.suppressed == []


def test_mute_persists_and_a_healthy_muted_project_is_still_listed(session, users, service, clock):
    stalled = add_project(session, users[0], "Stalled", idle=12)
    healthy = add_project(session, users[0], "Healthy", idle=0)
    service.update_prefs(stalled.id, ReminderPrefsUpdate(muted=True))
    service.update_prefs(healthy.id, ReminderPrefsUpdate(muted=True))
    clock.now = NOW + timedelta(days=200)

    overview = service.overview()

    assert overview.alerts == []
    assert {(s.slug, s.kind, s.muted) for s in overview.suppressed} == {
        ("stalled", ReminderKind.STALLED, True),
        ("healthy", ReminderKind.STALLED, True),
    }


def test_reactivating_clears_snooze_and_mute(session, users, service):
    project = add_project(session, users[0], "Rust", idle=12)
    service.update_prefs(project.id, ReminderPrefsUpdate(snooze_days=5, muted=True))

    prefs = service.update_prefs(project.id, ReminderPrefsUpdate.model_validate({"snooze_days": None, "muted": False}))

    assert (prefs.snoozed_until, prefs.muted) == (None, False)
    assert [a.slug for a in service.overview().alerts] == ["rust"]


def test_updating_one_field_leaves_the_other_alone(session, users, service):
    project = add_project(session, users[0], "Rust", idle=12)
    service.update_prefs(project.id, ReminderPrefsUpdate(snooze_days=5))

    prefs = service.update_prefs(project.id, ReminderPrefsUpdate(muted=True))

    assert prefs.snoozed_until == NOW + timedelta(days=5)
    assert prefs.muted is True


@pytest.mark.parametrize("days", [0, 31, -1])
def test_snooze_days_must_be_between_1_and_30(days):
    with pytest.raises(ValidationError):
        ReminderPrefsUpdate(snooze_days=days)


def test_get_prefs_defaults_when_no_row_exists(session, users, service):
    project = add_project(session, users[0], "Rust")

    prefs = service.get_prefs(project.id)

    assert (prefs.project_id, prefs.snoozed_until, prefs.muted) == (project.id, None, False)


# --- repeat rules -------------------------------------------------------------------------


def log(session, user, project, kind, days_ago, hour=12):
    sent = (NOW - timedelta(days=days_ago)).replace(hour=hour)
    session.add(ReminderLog(user_id=user.id, project_id=project.id, kind=kind, sent_at=sent, local_date=sent.date()))
    session.commit()


def test_a_stalled_project_with_no_reminder_yet_is_deliverable(session, users, service):
    add_project(session, users[0], "Rust", idle=12)

    assert [a.slug for a in service.deliverable()] == ["rust"]


def test_stalled_repeats_only_after_the_repeat_interval(session, users, service):
    project = add_project(session, users[0], "Rust", idle=30)
    log(session, users[0], project, ReminderKind.STALLED, days_ago=3)
    assert service.deliverable() == []

    session.query(ReminderLog).delete()
    log(session, users[0], project, ReminderKind.STALLED, days_ago=7, hour=14)
    assert [a.slug for a in service.deliverable()] == ["rust"]

    session.query(ReminderLog).delete()
    log(session, users[0], project, ReminderKind.STALLED, days_ago=6, hour=14)
    assert service.deliverable() == []


def test_stalled_stops_after_the_maximum_number_of_reminders_without_activity(session, users, service):
    project = add_project(session, users[0], "Rust", idle=60)
    for days_ago in (21, 14, 7):
        log(session, users[0], project, ReminderKind.STALLED, days_ago=days_ago, hour=10)

    assert service.deliverable() == []
    assert [a.slug for a in service.overview().alerts] == ["rust"]  # the dashboard keeps showing it


def test_new_activity_restarts_the_count(session, users, service):
    project = add_project(session, users[0], "Rust", idle=60)
    for days_ago in (21, 14, 7):
        log(session, users[0], project, ReminderKind.STALLED, days_ago=days_ago, hour=10)
    assert service.deliverable() == []

    project.last_activity_at = NOW - timedelta(days=8)  # touched between the 2nd and 3rd reminder
    session.commit()

    assert [a.slug for a in service.deliverable()] == ["rust"]


def test_ready_to_finish_is_announced_once_per_last_activity(session, users, service):
    project = add_project(session, users[0], "Done soon", idle=2, done=2, total=2)
    assert [a.slug for a in service.deliverable()] == ["done-soon"]

    log(session, users[0], project, ReminderKind.READY_TO_FINISH, days_ago=1)
    assert service.deliverable() == []

    project.last_activity_at = NOW  # new activity after the notice
    session.commit()
    assert [a.slug for a in service.deliverable()] == ["done-soon"]


def test_stalled_and_ready_to_finish_logs_are_independent(session, users, service):
    project = add_project(session, users[0], "Rust", idle=12, done=1, total=2)
    log(session, users[0], project, ReminderKind.READY_TO_FINISH, days_ago=1)

    assert [a.slug for a in service.deliverable()] == ["rust"]


def test_snoozed_projects_are_not_deliverable(session, users, service):
    project = add_project(session, users[0], "Rust", idle=12)
    service.update_prefs(project.id, ReminderPrefsUpdate(snooze_days=2))

    assert service.deliverable() == []


# --- delivery log -------------------------------------------------------------------------


def test_record_sent_writes_the_local_date_in_the_configured_zone(session, users, clock):
    project = add_project(session, users[0], "Rust", idle=12)
    clock.now = datetime(2026, 11, 6, 3, 0, tzinfo=UTC)  # 22:00 of Nov 5 in Guayaquil (UTC-5)
    service = service_for(session, users[0], clock)
    alerts = service.deliverable()

    service.record_sent(alerts)

    row = session.scalar(select(ReminderLog))
    assert (row.project_id, row.kind, row.sent_at, row.local_date) == (
        project.id,
        ReminderKind.STALLED,
        clock.now,
        date(2026, 11, 5),
    )
    assert service.has_digest_on(date(2026, 11, 5)) is True
    assert service.has_digest_on(date(2026, 11, 6)) is False


def test_record_sent_twice_the_same_day_keeps_a_single_row(session, users, service):
    add_project(session, users[0], "Rust", idle=12)
    alerts = service.overview().alerts

    service.record_sent(alerts)
    service.record_sent(alerts)

    assert session.scalar(select(func.count()).select_from(ReminderLog)) == 1


# --- isolation ----------------------------------------------------------------------------


def test_another_user_sees_none_of_my_alerts_prefs_or_logs(session, users, service, clock):
    mine = add_project(session, users[0], "Rust", idle=12)
    service.update_prefs(mine.id, ReminderPrefsUpdate(muted=True))
    service.record_sent(service.overview().alerts)
    other = service_for(session, users[1], clock)

    assert other.overview().alerts == []
    assert other.overview().suppressed == []
    assert other.has_digest_on(date(2026, 11, 5)) is False


def test_prefs_of_a_foreign_project_are_not_found(session, users, clock):
    foreign = add_project(session, users[1], "Theirs", idle=12)
    mine = service_for(session, users[0], clock)

    with pytest.raises(ProjectNotFound):
        mine.update_prefs(foreign.id, ReminderPrefsUpdate(muted=True))
    with pytest.raises(ProjectNotFound):
        mine.get_prefs(foreign.id)
    assert service_for(session, users[1], clock).get_prefs(foreign.id).muted is False
