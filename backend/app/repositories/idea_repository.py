from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.models import Idea


@dataclass(frozen=True)
class IdeaTotals:
    captured: int
    in_inbox: int
    assigned: int


class IdeaRepository:
    """Persistence only; every lookup is scoped by user_id."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get(self, user_id: int, idea_id: int) -> Idea | None:
        return self._session.scalar(select(Idea).where(Idea.user_id == user_id, Idea.id == idea_id))

    def list_by_project(self, user_id: int, project_id: int) -> list[Idea]:
        return list(
            self._session.scalars(
                select(Idea)
                .where(Idea.user_id == user_id, Idea.project_id == project_id)
                .order_by(Idea.id)
            )
        )

    def list_inbox(self, user_id: int) -> list[Idea]:
        return list(
            self._session.scalars(
                select(Idea)
                .where(Idea.user_id == user_id, Idea.project_id.is_(None))
                .order_by(Idea.id)
            )
        )

    def list_all(self, user_id: int) -> list[Idea]:
        # id breaks ties between ideas created within the same timestamp
        return list(
            self._session.scalars(
                select(Idea)
                .where(Idea.user_id == user_id)
                .order_by(Idea.created_at.desc(), Idea.id.desc())
            )
        )

    def created_times(self, user_id: int, since: datetime) -> list[datetime]:
        return list(
            self._session.scalars(
                select(Idea.created_at).where(Idea.user_id == user_id, Idea.created_at >= since)
            )
        )

    def assigned_times(self, user_id: int, since: datetime) -> list[datetime]:
        """assigned_at of ideas currently inside a project; inbox ideas never count."""
        return list(
            self._session.scalars(
                select(Idea.assigned_at).where(
                    Idea.user_id == user_id,
                    Idea.project_id.is_not(None),
                    Idea.assigned_at >= since,
                )
            )
        )

    def totals(self, user_id: int) -> IdeaTotals:
        in_inbox = func.coalesce(func.sum(case((Idea.project_id.is_(None), 1), else_=0)), 0)
        captured, inbox = self._session.execute(
            select(func.count(), in_inbox).where(Idea.user_id == user_id)
        ).one()
        return IdeaTotals(captured=captured, in_inbox=int(inbox), assigned=captured - int(inbox))

    def add(self, idea: Idea) -> None:
        self._session.add(idea)
        self._session.flush()

    def delete(self, idea: Idea) -> None:
        self._session.delete(idea)
        self._session.flush()
