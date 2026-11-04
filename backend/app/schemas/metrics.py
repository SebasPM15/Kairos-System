from datetime import date, datetime

from pydantic import BaseModel

from app.models import ProjectStatus


class StatusCount(BaseModel):
    status: ProjectStatus
    count: int


class ProjectProgress(BaseModel):
    id: int
    name: str
    status: ProjectStatus
    progress: int
    milestones_done: int
    milestones_total: int
    days_since_activity: int


class WeekCount(BaseModel):
    week_start: date
    count: int


class IdeaTotals(BaseModel):
    captured: int
    in_inbox: int
    assigned: int


class MetricsRead(BaseModel):
    generated_at: datetime
    timezone: str
    weeks: int
    current_week_start: date
    projects_by_status: list[StatusCount]
    project_progress: list[ProjectProgress]
    milestones_completed: list[WeekCount]
    ideas_captured: list[WeekCount]
    ideas_assigned: list[WeekCount]
    idea_totals: IdeaTotals
