from datetime import datetime

from pydantic import BaseModel, Field

from app.models import ProjectStatus, ReminderKind


class ReminderAlert(BaseModel):
    """A project that needs attention right now; computed on the fly, never stored."""

    project_id: int
    slug: str
    name: str
    status: ProjectStatus
    kind: ReminderKind
    days_idle: int
    # Days of inactivity that triggered a stalled alert; None for ready_to_finish
    threshold_days: int | None
    next_action: str | None
    milestones_total: int
    last_activity_at: datetime


class ReminderSuppressed(BaseModel):
    """A project whose reminders are snoozed or muted, listed so they can be reactivated."""

    project_id: int
    slug: str
    name: str
    status: ProjectStatus
    # What would alert if it were not suppressed; None when the project is healthy
    kind: ReminderKind | None
    snoozed_until: datetime | None
    muted: bool


class RemindersRead(BaseModel):
    alerts: list[ReminderAlert]
    suppressed: list[ReminderSuppressed]


class ReminderPrefsUpdate(BaseModel):
    # snooze_days sent as null clears the snooze; muted absent or null leaves it unchanged
    snooze_days: int | None = Field(default=None, ge=1, le=30)
    muted: bool | None = None


class ReminderPrefsRead(BaseModel):
    project_id: int
    snoozed_until: datetime | None
    muted: bool
