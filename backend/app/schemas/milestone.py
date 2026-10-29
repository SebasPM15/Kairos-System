from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class MilestoneCreate(BaseModel):
    title: str = Field(min_length=1, max_length=300)


class MilestoneUpdate(BaseModel):
    # Null means "unchanged" for every field
    title: str | None = Field(default=None, min_length=1, max_length=300)
    done: bool | None = None
    position: int | None = Field(default=None, ge=0)


class MilestoneRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    title: str
    done: bool
    position: int
    completed_at: datetime | None
    created_at: datetime
