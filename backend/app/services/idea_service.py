from sqlalchemy.orm import Session

from app.models import Idea, Project
from app.models.base import utcnow
from app.repositories.idea_repository import IdeaRepository
from app.repositories.project_repository import ProjectRepository
from app.schemas.idea import IdeaCreate, IdeaUpdate
from app.services.errors import IdeaNotFound, ProjectNotFound


class IdeaService:
    def __init__(
        self,
        session: Session,
        user_id: int,
        repository: IdeaRepository | None = None,
        projects: ProjectRepository | None = None,
    ) -> None:
        self._session = session
        self._user_id = user_id
        self._repo = repository or IdeaRepository(session)
        self._projects = projects or ProjectRepository(session)

    def create(self, data: IdeaCreate) -> Idea:
        project = self._get_project(data.project_id) if data.project_id is not None else None
        idea = Idea(user_id=self._user_id, project_id=data.project_id, content=data.content)
        self._repo.add(idea)
        if project is not None:
            project.last_activity_at = utcnow()
        self._session.commit()
        return idea

    def list_by_project(self, project_id: int) -> list[Idea]:
        self._get_project(project_id)
        return self._repo.list_by_project(self._user_id, project_id)

    def list_inbox(self) -> list[Idea]:
        return self._repo.list_inbox(self._user_id)

    def update(self, idea_id: int, data: IdeaUpdate) -> Idea:
        idea = self._get(idea_id)
        # model_fields_set tells an omitted project_id apart from an explicit null (back to inbox)
        if "content" in data.model_fields_set:
            idea.content = data.content
        if "project_id" in data.model_fields_set:
            self._assign(idea, data.project_id)
        self._session.commit()
        return idea

    def delete(self, idea_id: int) -> None:
        self._repo.delete(self._get(idea_id))
        self._session.commit()

    def _assign(self, idea: Idea, project_id: int | None) -> None:
        if project_id is None:
            idea.project_id = None
            return
        project = self._get_project(project_id)
        if idea.project_id != project.id:
            idea.project_id = project.id
            project.last_activity_at = utcnow()

    def _get(self, idea_id: int) -> Idea:
        idea = self._repo.get(self._user_id, idea_id)
        if idea is None:
            raise IdeaNotFound(idea_id)
        return idea

    def _get_project(self, project_id: int) -> Project:
        project = self._projects.get(self._user_id, project_id)
        if project is None:
            raise ProjectNotFound(project_id)
        return project
