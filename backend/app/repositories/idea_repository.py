from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Idea


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

    def add(self, idea: Idea) -> None:
        self._session.add(idea)
        self._session.flush()

    def delete(self, idea: Idea) -> None:
        self._session.delete(idea)
        self._session.flush()
