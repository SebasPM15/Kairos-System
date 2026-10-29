from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.models import Milestone, Project


class MilestoneRepository:
    """Persistence only; every lookup is scoped by user_id through the owning project."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get(self, user_id: int, milestone_id: int) -> Milestone | None:
        return self._session.scalar(
            select(Milestone)
            .join(Project)
            .where(Project.user_id == user_id, Milestone.id == milestone_id)
        )

    def list_by_project(self, user_id: int, project_id: int) -> list[Milestone]:
        return list(
            self._session.scalars(
                select(Milestone)
                .join(Project)
                .where(Project.user_id == user_id, Milestone.project_id == project_id)
                .order_by(Milestone.position, Milestone.id)
            )
        )

    def counts_by_project(self, user_id: int, project_ids: list[int]) -> dict[int, tuple[int, int]]:
        """Return {project_id: (done, total)}; projects without milestones are absent."""
        done = func.coalesce(func.sum(case((Milestone.done, 1), else_=0)), 0)
        rows = self._session.execute(
            select(Milestone.project_id, done, func.count())
            .join(Project)
            .where(Project.user_id == user_id, Milestone.project_id.in_(project_ids))
            .group_by(Milestone.project_id)
        )
        return {project_id: (int(d), int(total)) for project_id, d, total in rows}

    def add(self, milestone: Milestone) -> None:
        self._session.add(milestone)
        self._session.flush()

    def delete(self, milestone: Milestone) -> None:
        self._session.delete(milestone)
        self._session.flush()
