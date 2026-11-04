from collections.abc import Callable
from datetime import datetime

from sqlalchemy.orm import Session

from app.config import Settings
from app.models import ProjectStatus
from app.models.base import utcnow
from app.repositories.idea_repository import IdeaRepository
from app.repositories.milestone_repository import MilestoneRepository
from app.repositories.project_repository import ProjectRepository
from app.schemas.metrics import (
    IdeaTotals,
    MetricsRead,
    ProjectProgress,
    StatusCount,
    WeekCount,
)
from app.services.project_service import ProjectService
from app.services.weeks import WeekBucket, current_week_start, week_buckets, window_start

# Display order: active work first
_PROGRESS_ORDER = [
    ProjectStatus.ACTIVE,
    ProjectStatus.IDEA,
    ProjectStatus.PAUSED,
    ProjectStatus.DONE,
]
_STATUS_ORDER = [
    ProjectStatus.IDEA,
    ProjectStatus.ACTIVE,
    ProjectStatus.PAUSED,
    ProjectStatus.DONE,
]


def _to_counts(buckets: list[WeekBucket]) -> list[WeekCount]:
    return [WeekCount(week_start=b.week_start, count=b.count) for b in buckets]


class MetricsService:
    def __init__(
        self,
        session: Session,
        user_id: int,
        settings: Settings,
        clock: Callable[[], datetime] = utcnow,
    ) -> None:
        self._user_id = user_id
        self._settings = settings
        self._clock = clock
        self._projects = ProjectRepository(session)
        self._milestones = MilestoneRepository(session)
        self._ideas = IdeaRepository(session)
        self._project_service = ProjectService(session, user_id, settings)

    def get(self, weeks: int) -> MetricsRead:
        now = self._clock()
        tz = self._settings.tzinfo
        since = window_start(now, weeks, tz)

        def series(times: list[datetime]) -> list[WeekCount]:
            return _to_counts(week_buckets(times, now, weeks, tz))

        by_status = self._projects.count_by_status(self._user_id)
        totals = self._ideas.totals(self._user_id)
        return MetricsRead(
            generated_at=now,
            timezone=self._settings.timezone,
            weeks=weeks,
            current_week_start=current_week_start(now, tz),
            projects_by_status=[
                StatusCount(status=status, count=by_status.get(status, 0))
                for status in _STATUS_ORDER
            ],
            project_progress=self._progress(),
            milestones_completed=series(self._milestones.completion_times(self._user_id, since)),
            ideas_captured=series(self._ideas.created_times(self._user_id, since)),
            ideas_assigned=series(self._ideas.assigned_times(self._user_id, since)),
            idea_totals=IdeaTotals(
                captured=totals.captured, in_inbox=totals.in_inbox, assigned=totals.assigned
            ),
        )

    def _progress(self) -> list[ProjectProgress]:
        # sorted() is stable, so projects keep their id order inside each status
        projects = sorted(
            self._project_service.list(), key=lambda p: _PROGRESS_ORDER.index(p.status)
        )
        return [
            ProjectProgress(
                id=p.id,
                name=p.name,
                status=p.status,
                progress=p.progress,
                milestones_done=p.milestones_done,
                milestones_total=p.milestones_total,
                days_since_activity=p.days_since_activity,
            )
            for p in projects
        ]
