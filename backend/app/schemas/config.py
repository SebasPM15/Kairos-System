from pydantic import BaseModel


class PublicConfig(BaseModel):
    max_active_projects: int
