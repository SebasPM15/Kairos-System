import asyncio
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import sessionmaker

from app.bot import messages
from app.config import Settings
from app.models import ProjectStatus, ReminderKind, ReminderLog
from app.schemas.reminder import ReminderAlert
from app.services.reminder_digest import Digest, deliver_digest, is_quiet_hour
from tests.test_reminder_service import NOW, Clock, add_project

# NOW is 10:00 in Guayaquil (UTC-5), outside the quiet hours 21:00-08:00


@pytest.fixture
def clock():
    return Clock()


@pytest.fixture
def deliver(session, users, clock):
    factory = sessionmaker(bind=session.get_bind(), expire_on_commit=False)
    sent: list[Digest] = []

    async def send(digest: Digest) -> None:
        sent.append(digest)

    def call(settings: Settings | None = None, send_fn=None, user=None) -> bool:
        return asyncio.run(
            deliver_digest(
                (user or users[0]).id,
                session_factory=factory,
                settings=settings or Settings(),
                clock=clock,
                send=send_fn or send,
            )
        )

    call.sent = sent
    return call


def log_count(session) -> int:
    session.expire_all()
    return session.scalar(select(func.count()).select_from(ReminderLog))


@pytest.mark.parametrize(
    ("hour", "quiet"),
    [(21, True), (23, True), (0, True), (7, True), (8, False), (12, False), (20, False)],
)
def test_default_quiet_hours_cross_midnight(hour, quiet):
    assert is_quiet_hour(hour, 21, 8) is quiet


def test_quiet_hours_inside_a_single_day():
    assert [h for h in range(24) if is_quiet_hour(h, 13, 15)] == [13, 14]


def test_one_digest_lists_active_projects_longest_idle_first_and_counts_the_paused(session, users, deliver):
    add_project(session, users[0], "Young", idle=8)
    add_project(session, users[0], "Old", idle=20)
    add_project(session, users[0], "Resting", status=ProjectStatus.PAUSED, idle=60)
    add_project(session, users[0], "Fresh", idle=1)

    assert deliver() is True

    digest = deliver.sent[0]
    assert [a.slug for a in digest.items] == ["old", "young"]
    assert [a.slug for a in digest.paused] == ["resting"]
    assert digest.overflow == 0
    assert log_count(session) == 3


def test_only_one_digest_per_local_day_even_with_items_left_out(session, users, deliver, clock):
    for n in range(7):
        add_project(session, users[0], f"P{n}", idle=10 + n)

    assert deliver() is True
    assert (len(deliver.sent[0].items), deliver.sent[0].overflow) == (5, 2)
    assert log_count(session) == 5  # the two left out are not marked as told

    clock.now = NOW + timedelta(hours=2)
    assert deliver() is False

    clock.now = NOW + timedelta(days=1)
    assert deliver() is True
    assert [a.slug for a in deliver.sent[1].items] == ["p1", "p0"]  # the left-out ones; the rest repeat in 7 days
    assert log_count(session) == 7


def test_a_digest_of_only_paused_projects_is_still_sent(session, users, deliver):
    add_project(session, users[0], "Resting", status=ProjectStatus.PAUSED, idle=47)

    assert deliver() is True

    assert deliver.sent[0].items == []
    assert len(deliver.sent[0].paused) == 1


def test_nothing_due_sends_nothing(session, users, deliver):
    add_project(session, users[0], "Fresh", idle=1)

    assert deliver() is False
    assert deliver.sent == []
    assert log_count(session) == 0


def test_disabled_reminders_send_nothing(session, users, deliver):
    add_project(session, users[0], "Old", idle=20)

    assert deliver(Settings(reminders_enabled=False)) is False
    assert deliver.sent == []


@pytest.mark.parametrize(
    ("utc", "sends"),
    [
        (datetime(2026, 11, 6, 1, 59, tzinfo=UTC), True),  # 20:59 local
        (datetime(2026, 11, 6, 2, 0, tzinfo=UTC), False),  # 21:00 local, quiet starts
        (datetime(2026, 11, 6, 5, 30, tzinfo=UTC), False),  # 00:30 local, after midnight
        (datetime(2026, 11, 6, 12, 59, tzinfo=UTC), False),  # 07:59 local
        (datetime(2026, 11, 6, 13, 0, tzinfo=UTC), True),  # 08:00 local, first tick after the silence
    ],
)
def test_quiet_hours_use_the_local_zone_and_cross_midnight(session, users, deliver, clock, utc, sends):
    add_project(session, users[0], "Old", idle=20)
    clock.now = utc

    assert deliver() is sends
    assert len(deliver.sent) == int(sends)
    assert log_count(session) == int(sends)


def test_silence_defers_instead_of_discarding(session, users, deliver, clock):
    add_project(session, users[0], "Old", idle=20)
    clock.now = datetime(2026, 11, 6, 4, 0, tzinfo=UTC)  # 23:00 local
    assert deliver() is False

    clock.now = datetime(2026, 11, 6, 13, 0, tzinfo=UTC)  # 08:00 local
    assert deliver() is True
    assert [a.slug for a in deliver.sent[0].items] == ["old"]


def test_after_a_week_off_a_single_capped_digest_goes_out(session, users, deliver, clock):
    for n in range(12):
        add_project(session, users[0], f"P{n}", idle=14 + n)
    add_project(session, users[0], "Resting", status=ProjectStatus.PAUSED, idle=90)

    assert deliver() is True
    clock.now = NOW + timedelta(minutes=30)
    assert deliver() is False

    assert len(deliver.sent) == 1
    digest = deliver.sent[0]
    assert (len(digest.items), digest.overflow, len(digest.paused)) == (5, 7, 1)
    assert [a.days_idle for a in digest.items] == sorted((a.days_idle for a in digest.items), reverse=True)


def test_a_failed_send_is_not_logged_and_the_next_attempt_goes_through(session, users, deliver, clock):
    add_project(session, users[0], "Old", idle=20)

    async def failing(digest):
        raise RuntimeError("network down")

    with pytest.raises(RuntimeError):
        deliver(send_fn=failing)
    assert log_count(session) == 0

    clock.now = NOW + timedelta(minutes=30)
    assert deliver() is True
    assert log_count(session) == 1


def test_digest_of_one_user_ignores_the_projects_of_another(session, users, deliver):
    add_project(session, users[1], "Theirs", idle=40)

    assert deliver() is False
    assert deliver(user=users[1]) is True


# --- message text -------------------------------------------------------------------------


def alert(**overrides) -> ReminderAlert:
    values = dict(
        project_id=1,
        slug="curso-de-rust",
        name="Curso de Rust",
        status=ProjectStatus.ACTIVE,
        kind=ReminderKind.STALLED,
        days_idle=12,
        threshold_days=7,
        next_action="Resolver los ejercicios",
        milestones_total=5,
        last_activity_at=NOW,
    )
    return ReminderAlert(**{**values, **overrides})


def test_digest_text_lists_numbered_items_overflow_and_the_paused_line():
    ready = alert(slug="portafolio", kind=ReminderKind.READY_TO_FINISH, threshold_days=None)
    digest = Digest(items=[alert(), ready], paused=[alert(slug="a"), alert(slug="b")], overflow=3)

    assert messages.digest_text(digest, 30).splitlines() == [
        "Recordatorios",
        "1. curso-de-rust: 12 días sin avance. Próxima acción: Resolver los ejercicios",
        "2. portafolio: todos los hitos están hechos. Usa /terminar portafolio o agrega más con /hito.",
        "Hay 3 más en /recordatorios.",
        "Y 2 proyectos en pausa llevan más de 30 días: /recordatorios",
    ]


def test_digest_text_uses_singulars():
    digest = Digest(items=[alert(days_idle=1)], paused=[alert(slug="a")], overflow=0)

    lines = messages.digest_text(digest, 30).splitlines()

    assert lines[1].startswith("1. curso-de-rust: 1 día sin avance.")
    assert lines[2] == "Y 1 proyecto en pausa lleva más de 30 días: /recordatorios"


def test_alert_line_mentions_missing_milestones_and_trims_long_actions():
    line = messages.alert_line(alert(milestones_total=0, next_action="x" * 300))

    assert "Aún no tiene hitos." in line
    assert line.endswith("…")
    assert len(line) < 240


def test_alert_line_without_next_action_has_no_trailing_label():
    assert messages.alert_line(alert(next_action=None)) == "curso-de-rust: 12 días sin avance."
