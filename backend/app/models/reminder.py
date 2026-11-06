import enum
from datetime import date, datetime

from sqlalchemy import Date, Enum, ForeignKey, Index, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.models.base import UTCDateTime, utcnow


class ReminderKind(str, enum.Enum):
    STALLED = "stalled"
    READY_TO_FINISH = "ready_to_finish"


class ReminderLog(Base):
    """One row per reminder the bot delivered; append-only. Alerts themselves are computed live."""

    __tablename__ = "reminder_log"
    __table_args__ = (
        UniqueConstraint("user_id", "project_id", "kind", "local_date", name="uq_reminder_log_per_day"),
        Index("ix_reminder_log_user_id_sent_at", "user_id", "sent_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"))
    kind: Mapped[ReminderKind] = mapped_column(
        Enum(ReminderKind, native_enum=False, values_callable=lambda e: [m.value for m in e])
    )
    sent_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow)
    # The day of sending in TIMEZONE; one daily digest per user is decided on it
    local_date: Mapped[date] = mapped_column(Date)


class ProjectReminderPrefs(Base):
    """Snooze and mute for one project; no row means defaults."""

    __tablename__ = "project_reminder_prefs"

    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    snoozed_until: Mapped[datetime | None] = mapped_column(UTCDateTime())
    muted: Mapped[bool] = mapped_column(default=False)
