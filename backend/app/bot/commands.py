"""One function per bot command: (session, user_id, args) -> reply text.

Handlers stay thin; everything here goes through the services.
"""

from collections.abc import Callable
from functools import wraps

from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.bot import messages
from app.bot.parsing import parse_id, parse_idea, split_slug, split_title_rationale
from app.config import get_settings
from app.models import ProjectStatus
from app.schemas.decision import DecisionCreate
from app.schemas.idea import IdeaCreate
from app.schemas.milestone import MilestoneCreate, MilestoneUpdate
from app.schemas.project import ProjectCreate, ProjectRead, ProjectUpdate
from app.services.decision_service import DecisionService
from app.services.errors import DomainError, ProjectNotFound
from app.services.idea_service import IdeaService
from app.services.milestone_service import MilestoneService
from app.services.project_service import ProjectService

# Telegram rejects messages longer than this
MAX_MESSAGE_LENGTH = 4096

Command = Callable[[Session, int, str], str]


def _reply(command: Command) -> Command:
    """Turn domain/validation errors into messages and cap the reply length."""

    @wraps(command)
    def wrapper(session: Session, user_id: int, args: str) -> str:
        try:
            text = command(session, user_id, args)
        except DomainError as error:
            text = messages.error_message(error)
        except ValidationError:
            text = messages.INVALID_INPUT
        if len(text) > MAX_MESSAGE_LENGTH:
            text = text[: MAX_MESSAGE_LENGTH - 1] + "…"
        return text

    return wrapper


def _projects(session: Session, user_id: int) -> ProjectService:
    return ProjectService(session, user_id, get_settings())


def _by_slug(projects: list[ProjectRead], slug: str) -> ProjectRead:
    for project in projects:
        if project.slug == slug:
            return project
    raise ProjectNotFound(slug)


@_reply
def proyecto(session: Session, user_id: int, args: str) -> str:
    name = args.strip()
    if not name:
        return messages.USAGE["proyecto"]
    project = _projects(session, user_id).create(ProjectCreate(name=name))
    return (
        f"Proyecto creado: {project.name} (slug: {project.slug}), estado: idea.\n"
        f"Actívalo con /foco {project.slug}: <próxima acción>."
    )


@_reply
def idea(session: Session, user_id: int, args: str) -> str:
    projects = _projects(session, user_id).list()
    slug, content = parse_idea(args, {p.slug for p in projects})
    if not content:
        return messages.USAGE["idea"]
    project = _by_slug(projects, slug) if slug else None
    IdeaService(session, user_id).create(
        IdeaCreate(content=content, project_id=project.id if project else None)
    )
    return f"Idea guardada en {project.slug}." if project else "Idea guardada en la bandeja de entrada."


@_reply
def hito(session: Session, user_id: int, args: str) -> str:
    parsed = split_slug(args)
    if parsed is None:
        return messages.USAGE["hito"]
    slug, title = parsed
    project = _by_slug(_projects(session, user_id).list(), slug)
    milestone = MilestoneService(session, user_id).create(project.id, MilestoneCreate(title=title))
    return f"Hito #{milestone.id} creado en {project.slug}: {milestone.title}"


@_reply
def hecho(session: Session, user_id: int, args: str) -> str:
    milestone_id = parse_id(args)
    if milestone_id is None:
        return messages.USAGE["hecho"]
    milestone = MilestoneService(session, user_id).update(milestone_id, MilestoneUpdate(done=True))
    project = _projects(session, user_id).get(milestone.project_id)
    lines = [
        f"Hecho: #{milestone.id} {milestone.title}",
        f"{project.name}: {project.progress}% ({project.milestones_done}/{project.milestones_total})",
    ]
    # Only a hint: the status never changes on its own
    if project.progress == 100 and project.status is not ProjectStatus.DONE:
        lines.append(messages.all_milestones_done(project.slug))
    return "\n".join(lines)


@_reply
def ayuda(session: Session, user_id: int, args: str) -> str:
    return messages.HELP


def _set_status(session: Session, user_id: int, slug: str, status: ProjectStatus) -> ProjectRead:
    service = _projects(session, user_id)
    project = _by_slug(service.list(), slug)
    return service.update(project.id, ProjectUpdate(status=status))


@_reply
def pausa(session: Session, user_id: int, args: str) -> str:
    slug = args.strip().lower()
    if not slug:
        return messages.USAGE["pausa"]
    project = _set_status(session, user_id, slug, ProjectStatus.PAUSED)
    return f"{project.name} en pausa. La próxima acción se conserva."


@_reply
def terminar(session: Session, user_id: int, args: str) -> str:
    slug = args.strip().lower()
    if not slug:
        return messages.USAGE["terminar"]
    project = _set_status(session, user_id, slug, ProjectStatus.DONE)
    return f"{project.name} terminado."


@_reply
def estado(session: Session, user_id: int, args: str) -> str:
    projects = _projects(session, user_id).list()
    slug = args.strip().lower()
    if slug:
        return _project_detail(session, user_id, _by_slug(projects, slug))
    if not projects:
        return messages.NO_PROJECTS
    return "\n\n".join(_project_summary(p) for p in projects)


@_reply
def foco(session: Session, user_id: int, args: str) -> str:
    parsed = split_slug(args)
    if parsed is None:
        return messages.USAGE["foco"]
    slug, next_action = parsed
    service = _projects(session, user_id)
    project = _by_slug(service.list(), slug)
    # One update: activation is validated against the new next_action and the limit
    project = service.update(
        project.id, ProjectUpdate(status=ProjectStatus.ACTIVE, next_action=next_action)
    )
    return f"Foco en {project.name}: activo.\nPróxima acción: {project.next_action}"


@_reply
def decision(session: Session, user_id: int, args: str) -> str:
    parsed = split_slug(args)
    pair = split_title_rationale(parsed[1]) if parsed else None
    if parsed is None or pair is None:
        return messages.USAGE["decision"]
    project = _by_slug(_projects(session, user_id).list(), parsed[0])
    title, rationale = pair
    DecisionService(session, user_id).create(
        project.id, DecisionCreate(title=title, rationale=rationale)
    )
    return f"Decisión registrada en {project.slug}: {title}"


def pending_milestones(session: Session, user_id: int) -> list[tuple[int, str]]:
    """(milestone id, "slug: title") of every unfinished milestone, for the /hecho keyboard."""
    milestones = MilestoneService(session, user_id)
    return [
        (m.id, f"{project.slug}: {m.title}")
        for project in _projects(session, user_id).list()
        for m in milestones.list(project.id)
        if not m.done
    ]


def _project_summary(project: ProjectRead) -> str:
    lines = [
        f"{project.name} [{project.slug}] - {messages.STATUS_LABELS[project.status]}, "
        f"{project.progress}% ({project.milestones_done}/{project.milestones_total}), "
        f"{messages.days_label(project.days_since_activity)}"
    ]
    if project.next_action:
        lines.append(f"Próxima: {project.next_action}")
    return "\n".join(lines)


def _project_detail(session: Session, user_id: int, project: ProjectRead) -> str:
    lines = [_project_summary(project)]
    milestones = MilestoneService(session, user_id).list(project.id)
    if not milestones:
        lines.append("Sin hitos.")
    lines += [f"[{'x' if m.done else ' '}] #{m.id} {m.title}" for m in milestones]
    return "\n".join(lines)
