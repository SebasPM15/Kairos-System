from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field, computed_field

from app.models import Project, ProjectStatus


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str = ""


class ProjectUpdate(BaseModel):
    # Only next_action may be sent as null (to clear it); null elsewhere means "unchanged"
    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    status: ProjectStatus | None = None
    next_action: str | None = None


class ProjectRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    slug: str
    description: str
    status: ProjectStatus
    next_action: str | None
    last_activity_at: datetime
    created_at: datetime
    # Derived from milestones by ProjectService (the only builder); never stored
    progress: int = Field(ge=0, le=100)
    milestones_done: int
    milestones_total: int

    @classmethod
    def from_project(cls, project: Project, *, done: int, total: int, progress: int) -> "ProjectRead":
        return cls(
            id=project.id,
            name=project.name,
            slug=project.slug,
            description=project.description,
            status=project.status,
            next_action=project.next_action,
            last_activity_at=project.last_activity_at,
            created_at=project.created_at,
            progress=progress,
            milestones_done=done,
            milestones_total=total,
        )

    @computed_field
    @property
    def days_since_activity(self) -> int:
        return (datetime.now(UTC) - self.last_activity_at).days
