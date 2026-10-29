"""Exports the current user's projects to the vault through the services and a VaultWriter."""

from sqlalchemy.orm import Session

from app.config import Settings
from app.exporters import markdown
from app.exporters.vault import FileSystemVaultWriter, VaultWriter
from app.schemas.decision import DecisionRead
from app.schemas.export import ExportSummary
from app.schemas.idea import IdeaRead
from app.schemas.milestone import MilestoneRead
from app.schemas.project import ProjectRead
from app.services.decision_service import DecisionService
from app.services.idea_service import IdeaService
from app.services.milestone_service import MilestoneService
from app.services.project_service import ProjectService

INBOX_FILE = "_bandeja.md"


class ProjectExporter:
    def __init__(
        self,
        projects: ProjectService,
        milestones: MilestoneService,
        ideas: IdeaService,
        decisions: DecisionService,
        writer: VaultWriter,
    ) -> None:
        self._projects = projects
        self._milestones = milestones
        self._ideas = ideas
        self._decisions = decisions
        self._writer = writer

    def export(self) -> ExportSummary:
        projects = self._projects.list()
        files = [(INBOX_FILE, markdown.render_inbox(self._inbox()))]
        for project in projects:
            files += self._project_files(project)

        written = sum(self._writer.write(path, content) for path, content in files)
        slugs = {project.slug for project in projects}
        # Folders of deleted projects are reported but never removed
        orphans = [name for name in self._writer.list_folders() if name not in slugs]
        return ExportSummary(
            projects_exported=len(projects),
            files_written=written,
            files_unchanged=len(files) - written,
            orphans=orphans,
        )

    def _inbox(self) -> list[IdeaRead]:
        return [IdeaRead.model_validate(idea) for idea in self._ideas.list_inbox()]

    def _project_files(self, project: ProjectRead) -> list[tuple[str, str]]:
        milestones = [MilestoneRead.model_validate(m) for m in self._milestones.list(project.id)]
        ideas = [IdeaRead.model_validate(i) for i in self._ideas.list_by_project(project.id)]
        decisions = [DecisionRead.model_validate(d) for d in self._decisions.list(project.id)]
        folder = project.slug
        return [
            (f"{folder}/README.md", markdown.render_readme(project)),
            (f"{folder}/hitos.md", markdown.render_milestones(project, milestones)),
            (f"{folder}/ideas.md", markdown.render_ideas(project, ideas)),
            (f"{folder}/decisiones.md", markdown.render_decisions(project, decisions)),
        ]


def build_exporter(session: Session, user_id: int, settings: Settings) -> ProjectExporter:
    """Single wiring shared by the API and the bot; raises VaultNotConfigured if the vault is unusable."""
    return ProjectExporter(
        ProjectService(session, user_id, settings),
        MilestoneService(session, user_id),
        IdeaService(session, user_id),
        DecisionService(session, user_id),
        FileSystemVaultWriter(settings.obsidian_vault_path),
    )
