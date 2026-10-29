from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, StringConstraints

Title = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=300)]
Rationale = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=5000)]


class DecisionCreate(BaseModel):
    title: Title
    rationale: Rationale


class DecisionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    title: str
    rationale: str
    created_at: datetime
