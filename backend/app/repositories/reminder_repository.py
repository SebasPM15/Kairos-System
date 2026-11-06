from datetime import date, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import ProjectReminderPrefs, ReminderKind, ReminderLog


class ReminderRepository:
    """Persistence only; every lookup is scoped by user_id."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get_prefs(self, user_id: int, project_id: int) -> ProjectReminderPrefs | None:
        return self._session.scalar(
            select(ProjectReminderPrefs).where(
                ProjectReminderPrefs.user_id == user_id, ProjectReminderPrefs.project_id == project_id
            )
        )

    def list_prefs(self, user_id: int) -> list[ProjectReminderPrefs]:
        return list(
            self._session.scalars(
                select(ProjectReminderPrefs)
                .where(ProjectReminderPrefs.user_id == user_id)
                .order_by(ProjectReminderPrefs.project_id)
            )
        )

    def add_prefs(self, prefs: ProjectReminderPrefs) -> None:
        self._session.add(prefs)
        self._session.flush()

    def list_logs(self, user_id: int, project_ids: list[int]) -> list[ReminderLog]:
        return list(
            self._session.scalars(
                select(ReminderLog)
                .where(ReminderLog.user_id == user_id, ReminderLog.project_id.in_(project_ids))
                .order_by(ReminderLog.sent_at, ReminderLog.id)
            )
        )

    def has_log_on(self, user_id: int, local_date: date) -> bool:
        return (
            self._session.scalar(
                select(ReminderLog.id)
                .where(ReminderLog.user_id == user_id, ReminderLog.local_date == local_date)
                .limit(1)
            )
            is not None
        )

    def add_log(
        self, user_id: int, project_id: int, kind: ReminderKind, sent_at: datetime, local_date: date
    ) -> ReminderLog:
        log = ReminderLog(
            user_id=user_id, project_id=project_id, kind=kind, sent_at=sent_at, local_date=local_date
        )
        self._session.add(log)
        self._session.flush()
        return log
