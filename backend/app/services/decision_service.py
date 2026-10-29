from sqlalchemy.orm import Session

from app.models import Decision, Project
from app.models.base import utcnow
from app.repositories.decision_repository import DecisionRepository
from app.repositories.project_repository import ProjectRepository
from app.schemas.decision import DecisionCreate
from app.services.errors import DecisionNotFound, ProjectNotFound


class DecisionService:
    def __init__(
        self,
        session: Session,
        user_id: int,
        repository: DecisionRepository | None = None,
        projects: ProjectRepository | None = None,
    ) -> None:
        self._session = session
        self._user_id = user_id
        self._repo = repository or DecisionRepository(session)
        self._projects = projects or ProjectRepository(session)

    def create(self, project_id: int, data: DecisionCreate) -> Decision:
        project = self._get_project(project_id)
        decision = Decision(project_id=project.id, title=data.title, rationale=data.rationale)
        self._repo.add(decision)
        project.last_activity_at = utcnow()
        self._session.commit()
        return decision

    def list(self, project_id: int) -> list[Decision]:
        self._get_project(project_id)
        return self._repo.list_by_project(self._user_id, project_id)

    def delete(self, decision_id: int) -> None:
        decision = self._repo.get(self._user_id, decision_id)
        if decision is None:
            raise DecisionNotFound(decision_id)
        self._repo.delete(decision)
        self._session.commit()

    def _get_project(self, project_id: int) -> Project:
        project = self._projects.get(self._user_id, project_id)
        if project is None:
            raise ProjectNotFound(project_id)
        return project
