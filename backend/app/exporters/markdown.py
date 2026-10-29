"""Pure Markdown rendering for the Obsidian export: data in, text out, no I/O."""

import json
import re
from collections.abc import Sequence
from datetime import UTC, datetime

from app.models import ProjectStatus
from app.schemas.decision import DecisionRead
from app.schemas.idea import IdeaRead
from app.schemas.milestone import MilestoneRead
from app.schemas.project import ProjectRead

NOTICE = "> Generado por Kairos desde la base de datos; los cambios manuales se sobrescriben."

_STATUS_LABELS = {
    ProjectStatus.IDEA: "idea",
    ProjectStatus.ACTIVE: "activo",
    ProjectStatus.PAUSED: "pausa",
    ProjectStatus.DONE: "terminado",
}

# Characters YAML 1.2 forbids or treats as line breaks, which json.dumps leaves untouched
_YAML_UNSAFE = re.compile("[\x7f-\x9f  ]")


def yaml_string(value: str) -> str:
    """Double-quoted YAML scalar; JSON strings are valid YAML, so quotes and colons stay inert."""
    quoted = json.dumps(value, ensure_ascii=False)
    return _YAML_UNSAFE.sub(lambda match: f"\\u{ord(match.group()):04x}", quoted)


def iso_utc(moment: datetime) -> str:
    return moment.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _day(moment: datetime) -> str:
    return moment.astimezone(UTC).strftime("%Y-%m-%d")


def _one_line(text: str) -> str:
    return " ".join(text.split())


def _indent_continuations(text: str) -> str:
    lines = text.strip().splitlines()
    return "\n".join([lines[0], *(f"  {line}" if line else "" for line in lines[1:])])


def render_readme(project: ProjectRead) -> str:
    next_action = yaml_string(project.next_action) if project.next_action else "null"
    frontmatter = [
        "---",
        f"status: {yaml_string(project.status.value)}",
        f"progress: {project.progress}",
        f"milestones_done: {project.milestones_done}",
        f"milestones_total: {project.milestones_total}",
        f"next_action: {next_action}",
        f"last_activity: {yaml_string(iso_utc(project.last_activity_at))}",
        "---",
    ]
    body = [
        NOTICE,
        f"# {_one_line(project.name)}",
        "\n".join(
            [
                f"- Estado: {_STATUS_LABELS[project.status]}",
                f"- Progreso: {project.progress} % "
                f"({project.milestones_done} de {project.milestones_total} hitos)",
                f"- Próxima acción: {_one_line(project.next_action or '') or 'sin definir'}",
            ]
        ),
        project.description.strip() or "_Sin descripción._",
        "[Hitos](hitos.md) · [Ideas](ideas.md) · [Decisiones](decisiones.md)",
    ]
    return "\n".join(frontmatter) + "\n\n" + "\n\n".join(body) + "\n"


def render_milestones(project: ProjectRead, milestones: Sequence[MilestoneRead]) -> str:
    items = [
        f"- [{'x' if m.done else ' '}] {_one_line(m.title)}"
        for m in sorted(milestones, key=lambda m: m.position)
    ]
    return _document(f"Hitos — {_one_line(project.name)}", items, "_Sin hitos todavía._")


def render_ideas(project: ProjectRead, ideas: Sequence[IdeaRead]) -> str:
    return _document(f"Ideas — {_one_line(project.name)}", _idea_items(ideas), "_Sin ideas todavía._")


def render_inbox(ideas: Sequence[IdeaRead]) -> str:
    return _document("Bandeja de entrada", _idea_items(ideas), "_La bandeja está vacía._")


def render_decisions(project: ProjectRead, decisions: Sequence[DecisionRead]) -> str:
    entries = [
        f"## {_one_line(d.title)}\n\n_{_day(d.created_at)}_\n\n{d.rationale.strip()}" for d in decisions
    ]
    title = f"Decisiones — {_one_line(project.name)}"
    if not entries:
        return _document(title, [], "_Sin decisiones todavía._")
    return f"{NOTICE}\n\n# {title}\n\n" + "\n\n".join(entries) + "\n"


def _idea_items(ideas: Sequence[IdeaRead]) -> list[str]:
    return [f"- {_day(i.created_at)} · {_indent_continuations(i.content)}" for i in ideas]


def _document(title: str, items: list[str], empty: str) -> str:
    content = "\n".join(items) if items else empty
    return f"{NOTICE}\n\n# {title}\n\n{content}\n"
