from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Decision, Project


class DecisionRepository:
    """Persistence only; every lookup is scoped by user_id through the owning project."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get(self, user_id: int, decision_id: int) -> Decision | None:
        return self._session.scalar(
            select(Decision)
            .join(Project)
            .where(Project.user_id == user_id, Decision.id == decision_id)
        )

    def list_by_project(self, user_id: int, project_id: int) -> list[Decision]:
        return list(
            self._session.scalars(
                select(Decision)
                .join(Project)
                .where(Project.user_id == user_id, Decision.project_id == project_id)
                .order_by(Decision.id)
            )
        )

    def add(self, decision: Decision) -> None:
        self._session.add(decision)
        self._session.flush()

    def delete(self, decision: Decision) -> None:
        self._session.delete(decision)
        self._session.flush()
