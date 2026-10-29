from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Project, ProjectStatus


class ProjectRepository:
    """Persistence only; every lookup is scoped by user_id."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get(self, user_id: int, project_id: int) -> Project | None:
        return self._session.scalar(
            select(Project).where(Project.user_id == user_id, Project.id == project_id)
        )

    def get_by_slug(self, user_id: int, slug: str) -> Project | None:
        return self._session.scalar(
            select(Project).where(Project.user_id == user_id, Project.slug == slug)
        )

    def list_by_user(self, user_id: int) -> list[Project]:
        return list(
            self._session.scalars(
                select(Project).where(Project.user_id == user_id).order_by(Project.id)
            )
        )

    def count_active(self, user_id: int) -> int:
        return self._session.scalar(
            select(func.count())
            .select_from(Project)
            .where(Project.user_id == user_id, Project.status == ProjectStatus.ACTIVE)
        )

    def add(self, project: Project) -> None:
        self._session.add(project)
        self._session.flush()

    def delete(self, project: Project) -> None:
        self._session.delete(project)
        self._session.flush()
