from sqlalchemy.orm import Session

from app.models import Milestone, Project
from app.models.base import utcnow
from app.repositories.milestone_repository import MilestoneRepository
from app.repositories.project_repository import ProjectRepository
from app.schemas.milestone import MilestoneCreate, MilestoneUpdate
from app.services.errors import MilestoneNotFound, ProjectNotFound


def calculate_progress(done: int, total: int) -> int:
    """Whole percentage of completed milestones; floors so 100 means truly finished."""
    return done * 100 // total if total else 0


class MilestoneService:
    def __init__(
        self,
        session: Session,
        user_id: int,
        repository: MilestoneRepository | None = None,
        projects: ProjectRepository | None = None,
    ) -> None:
        self._session = session
        self._user_id = user_id
        self._repo = repository or MilestoneRepository(session)
        self._projects = projects or ProjectRepository(session)

    def create(self, project_id: int, data: MilestoneCreate) -> Milestone:
        project = self._get_project(project_id)
        position = len(self._repo.list_by_project(self._user_id, project_id))
        milestone = Milestone(project_id=project.id, title=data.title.strip(), position=position)
        self._repo.add(milestone)
        project.last_activity_at = utcnow()
        self._session.commit()
        return milestone

    def list(self, project_id: int) -> list[Milestone]:
        self._get_project(project_id)
        return self._repo.list_by_project(self._user_id, project_id)

    def update(self, milestone_id: int, data: MilestoneUpdate) -> Milestone:
        milestone = self._get(milestone_id)
        changes = data.model_dump(exclude_unset=True, exclude_none=True)

        if "title" in changes:
            milestone.title = changes["title"].strip()
        if "done" in changes and changes["done"] != milestone.done:
            self._set_done(milestone, changes["done"])
        if "position" in changes:
            self._move(milestone, changes["position"])
        self._session.commit()
        return milestone

    def delete(self, milestone_id: int) -> None:
        milestone = self._get(milestone_id)
        project_id = milestone.project_id
        self._repo.delete(milestone)
        self._renumber(self._repo.list_by_project(self._user_id, project_id))
        self._session.commit()

    def _get(self, milestone_id: int) -> Milestone:
        milestone = self._repo.get(self._user_id, milestone_id)
        if milestone is None:
            raise MilestoneNotFound(milestone_id)
        return milestone

    def _get_project(self, project_id: int) -> Project:
        project = self._projects.get(self._user_id, project_id)
        if project is None:
            raise ProjectNotFound(project_id)
        return project

    def _set_done(self, milestone: Milestone, done: bool) -> None:
        now = utcnow()
        milestone.done = done
        milestone.completed_at = now if done else None
        milestone.project.last_activity_at = now

    def _move(self, milestone: Milestone, position: int) -> None:
        others = [
            m
            for m in self._repo.list_by_project(self._user_id, milestone.project_id)
            if m.id != milestone.id
        ]
        others.insert(min(position, len(others)), milestone)
        self._renumber(others)

    @staticmethod
    def _renumber(ordered: list[Milestone]) -> None:
        for index, milestone in enumerate(ordered):
            milestone.position = index
