"""Decides whether the daily Telegram digest goes out now and what it contains.

Alerts are computed live, so a bot that was off for a week simply sends one digest when it is back:
nothing is queued and nothing piles up.
"""

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import datetime

from sqlalchemy.orm import Session

from app.config import Settings
from app.models import ProjectStatus
from app.schemas.reminder import ReminderAlert
from app.services.reminder_service import ReminderService

# Individually listed projects per digest; more would stop being a glance
MAX_DIGEST_ITEMS = 5

SessionFactory = Callable[[], Session]


@dataclass(frozen=True)
class Digest:
    # Active projects, longest idle first, each on its own line
    items: list[ReminderAlert]
    # Paused projects, only counted in a summary line
    paused: list[ReminderAlert]
    # Active alerts that did not fit; they wait for a later day
    overflow: int = 0
    logged: list[ReminderAlert] = field(init=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "logged", [*self.items, *self.paused])


def is_quiet_hour(hour: int, start: int, end: int) -> bool:
    """Quiet hours run from `start` to `end` (exclusive) and may cross midnight."""
    if start < end:
        return start <= hour < end
    return hour >= start or hour < end


def plan_digest(service: ReminderService, settings: Settings) -> Digest | None:
    """None when nothing should be sent now: disabled, quiet hours, already sent today or nothing due."""
    if not settings.reminders_enabled:
        return None
    local = service.now().astimezone(settings.tzinfo)
    if is_quiet_hour(local.hour, settings.reminder_quiet_start_hour, settings.reminder_quiet_end_hour):
        return None
    # One digest per local day, even when items were left out of it
    if service.has_digest_on(local.date()):
        return None
    due = service.deliverable()
    active = [a for a in due if a.status is not ProjectStatus.PAUSED]
    paused = [a for a in due if a.status is ProjectStatus.PAUSED]
    if not active and not paused:
        return None
    shown = active[:MAX_DIGEST_ITEMS]
    return Digest(items=shown, paused=paused, overflow=len(active) - len(shown))


async def deliver_digest(
    user_id: int,
    *,
    session_factory: SessionFactory,
    settings: Settings,
    clock: Callable[[], datetime],
    send: Callable[[Digest], Awaitable[None]],
) -> bool:
    """Plan, send, and only then write the log. A failed send raises and leaves no trace, so the next
    tick tries again. Database work runs in threads, one session per phase."""
    digest = await asyncio.to_thread(_plan, user_id, session_factory, settings, clock)
    if digest is None:
        return False
    await send(digest)
    await asyncio.to_thread(_record, user_id, session_factory, settings, clock, digest)
    return True


def _plan(user_id: int, session_factory: SessionFactory, settings: Settings, clock) -> Digest | None:
    with session_factory() as session:
        return plan_digest(ReminderService(session, user_id, settings, clock=clock), settings)


def _record(user_id: int, session_factory: SessionFactory, settings: Settings, clock, digest: Digest) -> None:
    with session_factory() as session:
        ReminderService(session, user_id, settings, clock=clock).record_sent(digest.logged)
