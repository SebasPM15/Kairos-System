import enum
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Enum, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.models.base import UTCDateTime, utcnow

if TYPE_CHECKING:
    from app.models.decision import Decision
    from app.models.idea import Idea
    from app.models.milestone import Milestone


class ProjectStatus(str, enum.Enum):
    IDEA = "idea"
    ACTIVE = "active"
    PAUSED = "paused"
    DONE = "done"


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    slug: Mapped[str] = mapped_column(String(200), unique=True)
    description: Mapped[str] = mapped_column(Text, default="")
    # Persist the lowercase values ("idea"), not the member names
    status: Mapped[ProjectStatus] = mapped_column(
        Enum(ProjectStatus, native_enum=False, values_callable=lambda e: [m.value for m in e]),
        default=ProjectStatus.IDEA,
    )
    next_action: Mapped[str | None] = mapped_column(Text)
    last_activity_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow)

    milestones: Mapped[list["Milestone"]] = relationship(
        back_populates="project",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="Milestone.position",
    )
    decisions: Mapped[list["Decision"]] = relationship(
        back_populates="project", cascade="all, delete-orphan", passive_deletes=True
    )
    # No delete cascade: the database nulls project_id (ON DELETE SET NULL)
    ideas: Mapped[list["Idea"]] = relationship(back_populates="project", passive_deletes=True)
