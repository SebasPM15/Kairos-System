from pydantic import BaseModel


class StaleAfterDays(BaseModel):
    active: int
    paused: int


class PublicConfig(BaseModel):
    max_active_projects: int
    stale_after_days: StaleAfterDays
