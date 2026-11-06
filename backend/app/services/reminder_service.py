from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable
from datetime import date, datetime, timedelta

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import Settings
from app.models import ProjectReminderPrefs, ProjectStatus, ReminderKind
from app.models.base import idle_days, utcnow
from app.repositories.reminder_repository import ReminderRepository
from app.schemas.project import ProjectRead
from app.schemas.reminder import (
    ReminderAlert,
    ReminderPrefsRead,
    ReminderPrefsUpdate,
    RemindersRead,
    ReminderSuppressed,
)
from app.services.project_service import ProjectService


class ReminderService:
    """Alerts are derived from the projects every time they are asked for; the only stored state is
    the delivery log (what the bot already said) and the per-project snooze/mute."""

    def __init__(
        self,
        session: Session,
        user_id: int,
        settings: Settings,
        clock: Callable[[], datetime] = utcnow,
        projects: ProjectService | None = None,
        repository: ReminderRepository | None = None,
    ) -> None:
        self._session = session
        self._user_id = user_id
        self._settings = settings
        self._clock = clock
        self._projects = projects or ProjectService(session, user_id, settings)
        self._repo = repository or ReminderRepository(session)

    def now(self) -> datetime:
        return self._clock()

    def overview(self) -> RemindersRead:
        now = self._clock()
        prefs = {p.project_id: p for p in self._repo.list_prefs(self._user_id)}
        alerts: list[ReminderAlert] = []
        suppressed: list[ReminderSuppressed] = []
        for project in self._projects.list():
            kind = self._classify(project, now)
            pref = prefs.get(project.id)
            snoozed_until = pref.snoozed_until if pref and pref.snoozed_until and pref.snoozed_until > now else None
            muted = bool(pref and pref.muted)
            if muted or snoozed_until:
                suppressed.append(
                    ReminderSuppressed(
                        project_id=project.id,
                        slug=project.slug,
                        name=project.name,
                        status=project.status,
                        kind=kind,
                        snoozed_until=snoozed_until,
                        muted=muted,
                    )
                )
            elif kind is not None:
                alerts.append(self._alert(project, kind, now))
        # The longest-idle project first
        alerts.sort(key=lambda a: (-a.days_idle, a.project_id))
        return RemindersRead(alerts=alerts, suppressed=suppressed)

    def deliverable(self) -> list[ReminderAlert]:
        """Alerts the bot may mention now: the repeat rules applied on top of the live alerts."""
        now = self._clock()
        alerts = self.overview().alerts
        sent: dict[tuple[int, ReminderKind], list[datetime]] = defaultdict(list)
        for log in self._repo.list_logs(self._user_id, [a.project_id for a in alerts]):
            sent[(log.project_id, log.kind)].append(log.sent_at)
        return [a for a in alerts if self._may_repeat(a, sent[(a.project_id, a.kind)], now)]

    def has_digest_on(self, local_date: date) -> bool:
        return self._repo.has_log_on(self._user_id, local_date)

    def local_date(self, moment: datetime) -> date:
        return moment.astimezone(self._settings.tzinfo).date()

    def record_sent(self, alerts: list[ReminderAlert]) -> None:
        """Call only after Telegram accepted the message. A row that already exists or whose
        project vanished in the meantime is skipped; the others are kept."""
        now = self._clock()
        today = self.local_date(now)
        for alert in alerts:
            try:
                with self._session.begin_nested():
                    self._repo.add_log(self._user_id, alert.project_id, alert.kind, now, today)
            except IntegrityError:
                continue
        self._session.commit()

    def get_prefs(self, project_id: int) -> ReminderPrefsRead:
        self._projects.get(project_id)
        return self._prefs_read(project_id, self._repo.get_prefs(self._user_id, project_id))

    def update_prefs(self, project_id: int, data: ReminderPrefsUpdate) -> ReminderPrefsRead:
        # ProjectService.get is scoped by user_id: another user's project raises ProjectNotFound
        self._projects.get(project_id)
        prefs = self._repo.get_prefs(self._user_id, project_id)
        if prefs is None:
            prefs = ProjectReminderPrefs(project_id=project_id, user_id=self._user_id, muted=False)
            self._repo.add_prefs(prefs)
        if "snooze_days" in data.model_fields_set:
            days = data.snooze_days
            prefs.snoozed_until = self._clock() + timedelta(days=days) if days is not None else None
        if data.muted is not None:
            prefs.muted = data.muted
        self._session.commit()
        return self._prefs_read(project_id, prefs)

    def _classify(self, project: ProjectRead, now: datetime) -> ReminderKind | None:
        idle = idle_days(project.last_activity_at, now)
        if project.status is ProjectStatus.ACTIVE:
            if project.milestones_total > 0 and project.milestones_done == project.milestones_total:
                return ReminderKind.READY_TO_FINISH
            if idle >= self._settings.stale_days_active:
                return ReminderKind.STALLED
        elif project.status is ProjectStatus.PAUSED and idle >= self._settings.stale_days_paused:
            return ReminderKind.STALLED
        return None

    def _threshold(self, project: ProjectRead) -> int:
        if project.status is ProjectStatus.PAUSED:
            return self._settings.stale_days_paused
        return self._settings.stale_days_active

    def _alert(self, project: ProjectRead, kind: ReminderKind, now: datetime) -> ReminderAlert:
        return ReminderAlert(
            project_id=project.id,
            slug=project.slug,
            name=project.name,
            status=project.status,
            kind=kind,
            days_idle=idle_days(project.last_activity_at, now),
            threshold_days=self._threshold(project) if kind is ReminderKind.STALLED else None,
            next_action=project.next_action,
            milestones_total=project.milestones_total,
            last_activity_at=project.last_activity_at,
        )

    def _may_repeat(self, alert: ReminderAlert, sent: list[datetime], now: datetime) -> bool:
        # Only reminders since the last real activity count: any activity restarts the streak
        since_activity = [s for s in sent if s >= alert.last_activity_at]
        if alert.kind is ReminderKind.READY_TO_FINISH:
            return not since_activity
        if len(since_activity) >= self._settings.reminder_max_repeats:
            return False
        return not since_activity or now - max(since_activity) >= timedelta(days=self._settings.reminder_repeat_days)

    @staticmethod
    def _prefs_read(project_id: int, prefs: ProjectReminderPrefs | None) -> ReminderPrefsRead:
        return ReminderPrefsRead(
            project_id=project_id,
            snoozed_until=prefs.snoozed_until if prefs else None,
            muted=bool(prefs and prefs.muted),
        )
