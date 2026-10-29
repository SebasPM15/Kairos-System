from __future__ import annotations

import re
import unicodedata

from sqlalchemy.orm import Session

from app.config import Settings
from app.models import Project, ProjectStatus
from app.models.base import utcnow
from app.repositories.milestone_repository import MilestoneRepository
from app.repositories.project_repository import ProjectRepository
from app.schemas.project import ProjectCreate, ProjectRead, ProjectUpdate
from app.services.errors import ActiveLimitReached, NextActionRequired, ProjectNotFound
from app.services.milestone_service import calculate_progress


def slugify(name: str) -> str:
    ascii_name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", ascii_name.lower()).strip("-") or "project"


class ProjectService:
    def __init__(
        self,
        session: Session,
        user_id: int,
        settings: Settings,
        repository: ProjectRepository | None = None,
        milestones: MilestoneRepository | None = None,
    ) -> None:
        self._session = session
        self._user_id = user_id
        self._settings = settings
        self._repo = repository or ProjectRepository(session)
        self._milestones = milestones or MilestoneRepository(session)

    def create(self, data: ProjectCreate) -> ProjectRead:
        project = Project(
            user_id=self._user_id,
            name=data.name,
            slug=self._unique_slug(data.name),
            description=data.description,
            status=ProjectStatus.IDEA,
        )
        self._repo.add(project)
        self._session.commit()
        return self._to_reads([project])[0]

    def list(self) -> list[ProjectRead]:
        return self._to_reads(self._repo.list_by_user(self._user_id))

    def get(self, project_id: int) -> ProjectRead:
        return self._to_reads([self._find(project_id)])[0]

    def update(self, project_id: int, data: ProjectUpdate) -> ProjectRead:
        project = self._find(project_id)
        changes = data.model_dump(exclude_unset=True)
        for field in ("name", "description", "status"):
            if changes.get(field) is None:
                changes.pop(field, None)
        if "next_action" in changes:
            changes["next_action"] = (changes["next_action"] or "").strip() or None

        self._check_activation(project, changes)
        for field, value in changes.items():
            setattr(project, field, value)
        project.last_activity_at = utcnow()
        self._session.commit()
        return self._to_reads([project])[0]

    def delete(self, project_id: int) -> None:
        self._repo.delete(self._find(project_id))
        self._session.commit()

    def _find(self, project_id: int) -> Project:
        project = self._repo.get(self._user_id, project_id)
        if project is None:
            raise ProjectNotFound(project_id)
        return project

    def _to_reads(self, projects: list[Project]) -> list[ProjectRead]:
        """Single place where derived milestone figures are computed; they are never persisted."""
        counts = self._milestones.counts_by_project(self._user_id, [p.id for p in projects])
        reads = []
        for project in projects:
            done, total = counts.get(project.id, (0, 0))
            reads.append(
                ProjectRead.from_project(
                    project, done=done, total=total, progress=calculate_progress(done, total)
                )
            )
        return reads

    def _check_activation(self, project: Project, changes: dict) -> None:
        status = changes.get("status", project.status)
        if status is not ProjectStatus.ACTIVE:
            return
        next_action = changes["next_action"] if "next_action" in changes else project.next_action
        if not next_action:
            raise NextActionRequired(project.id)
        # An already-active project does not compete with itself for a slot
        if (
            project.status is not ProjectStatus.ACTIVE
            and self._repo.count_active(self._user_id) >= self._settings.max_active_projects
        ):
            raise ActiveLimitReached(self._settings.max_active_projects)

    def _unique_slug(self, name: str) -> str:
        base = slugify(name)
        slug, n = base, 1
        while self._repo.get_by_slug(self._user_id, slug) is not None:
            n += 1
            slug = f"{base}-{n}"
        return slug
