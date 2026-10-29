from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, StringConstraints, field_validator

Content = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=5000)]


class IdeaCreate(BaseModel):
    content: Content
    # Omitted or null: the idea goes to the inbox
    project_id: int | None = None


class IdeaUpdate(BaseModel):
    # An absent field means "unchanged"; project_id explicitly null returns the idea to the inbox
    project_id: int | None = None
    content: Content | None = None

    @field_validator("content", mode="after")
    @classmethod
    def _content_not_null(cls, value: str | None) -> str:
        if value is None:
            raise ValueError("content cannot be null")
        return value


class IdeaRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int | None
    content: str
    created_at: datetime
