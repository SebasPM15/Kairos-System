from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field, computed_field

from app.models import ProjectStatus


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

    @computed_field
    @property
    def days_since_activity(self) -> int:
        return (datetime.now(UTC) - self.last_activity_at).days
