import json
from datetime import UTC, datetime, timedelta, timezone

import pytest

from app.exporters import markdown
from app.models import ProjectStatus
from app.schemas.decision import DecisionRead
from app.schemas.idea import IdeaRead
from app.schemas.milestone import MilestoneRead
from app.schemas.project import ProjectRead

WHEN = datetime(2026, 10, 28, 15, 30, 5, tzinfo=UTC)


def project(**overrides) -> ProjectRead:
    values = dict(
        id=1,
        name="Kairos",
        slug="kairos",
        description="Asistente personal",
        status=ProjectStatus.ACTIVE,
        next_action="Escribir tests",
        last_activity_at=WHEN,
        created_at=WHEN,
        progress=33,
        milestones_done=1,
        milestones_total=3,
    )
    return ProjectRead(**{**values, **overrides})


def milestone(id, title, done, position) -> MilestoneRead:
    return MilestoneRead(
        id=id, project_id=1, title=title, done=done, position=position,
        completed_at=None, created_at=WHEN,
    )


def idea(content, project_id=1) -> IdeaRead:
    return IdeaRead(id=1, project_id=project_id, content=content, created_at=WHEN)


def decision(title, rationale) -> DecisionRead:
    return DecisionRead(id=1, project_id=1, title=title, rationale=rationale, created_at=WHEN)


def test_readme_has_frontmatter_first_then_notice_and_description():
    text = markdown.render_readme(project())

    assert text.startswith(
        '---\nstatus: "active"\nprogress: 33\nmilestones_done: 1\nmilestones_total: 3\n'
        'next_action: "Escribir tests"\nlast_activity: "2026-10-28T15:30:05Z"\n---\n'
    )
    body = text.split("---\n", 2)[2]
    assert body.startswith("\n" + markdown.NOTICE)
    assert "# Kairos" in body
    assert "- Estado: activo" in body
    assert "- Progreso: 33 % (1 de 3 hitos)" in body
    assert "Asistente personal" in body
    assert text.endswith("\n")


def test_readme_without_next_action_or_description():
    text = markdown.render_readme(project(next_action=None, description="  ", status=ProjectStatus.IDEA))

    assert "next_action: null\n" in text
    assert "- Próxima acción: sin definir" in text
    assert "_Sin descripción._" in text


@pytest.mark.parametrize(
    "value",
    [
        'Revisar: ver "plan" B',
        "a: b # c",
        "- guion",
        "linea 1\nlinea 2",
        "back\\slash",
        "ñandú ✓",
        "x y",
        "x\x85y",
        "null",
        "123",
    ],
)
def test_frontmatter_strings_round_trip_as_json(value):
    quoted = markdown.yaml_string(value)

    assert json.loads(quoted) == value
    assert "\n" not in quoted
    assert not any(char in quoted for char in "  \x85")


def test_next_action_with_colon_and_quotes_stays_a_single_quoted_line():
    text = markdown.render_readme(project(next_action='Hablar con: "Ana"'))

    assert 'next_action: "Hablar con: \\"Ana\\""\n' in text


def test_last_activity_is_normalised_to_utc():
    local = datetime(2026, 10, 28, 10, 0, tzinfo=timezone(timedelta(hours=-5)))

    assert markdown.iso_utc(local) == "2026-10-28T15:00:00Z"


def test_milestones_are_a_checklist_ordered_by_position():
    text = markdown.render_milestones(
        project(), [milestone(2, "Segundo", False, 1), milestone(1, "Primero", True, 0)]
    )

    assert "- [x] Primero\n- [ ] Segundo\n" in text
    assert text.startswith(markdown.NOTICE)


def test_milestone_title_with_newline_stays_one_item():
    text = markdown.render_milestones(project(), [milestone(1, "uno\ndos", False, 0)])

    assert "- [ ] uno dos\n" in text


def test_empty_milestones():
    assert "_Sin hitos todavía._" in markdown.render_milestones(project(), [])


def test_ideas_list_with_dates_and_multiline_indent():
    text = markdown.render_ideas(project(), [idea("una"), idea("dos\ntres")])

    assert "- 2026-10-28 · una\n- 2026-10-28 · dos\n  tres\n" in text


def test_empty_ideas_and_inbox():
    assert "_Sin ideas todavía._" in markdown.render_ideas(project(), [])
    inbox = markdown.render_inbox([])
    assert "# Bandeja de entrada" in inbox
    assert "_La bandeja está vacía._" in inbox


def test_inbox_lists_ideas():
    assert "- 2026-10-28 · suelta\n" in markdown.render_inbox([idea("suelta", project_id=None)])


def test_decisions_show_title_date_and_rationale():
    text = markdown.render_decisions(project(), [decision("Usar SQLite", "Es local y simple")])

    assert "## Usar SQLite\n\n_2026-10-28_\n\nEs local y simple\n" in text


def test_empty_decisions():
    assert "_Sin decisiones todavía._" in markdown.render_decisions(project(), [])


def test_every_document_but_the_readme_starts_with_the_notice():
    p = project()
    documents = [
        markdown.render_milestones(p, []),
        markdown.render_ideas(p, []),
        markdown.render_decisions(p, []),
        markdown.render_inbox([]),
    ]

    assert all(doc.startswith(markdown.NOTICE) for doc in documents)
