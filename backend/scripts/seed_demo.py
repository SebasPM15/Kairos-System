"""Loads demo data through the services so every business rule applies (active limit, next action,
computed progress). Run from backend/: python scripts/seed_demo.py [--reset] [--database-url URL]

It only ever touches a database whose file name contains "demo"; the real one is never a valid target.
"""

import argparse
import os
import sys
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path

from sqlalchemy import create_engine, func, inspect, select
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from app.config import Settings
from app.models import Idea, Milestone, Project, ProjectStatus
from app.models.base import utcnow
from app.schemas.decision import DecisionCreate
from app.schemas.idea import IdeaCreate
from app.schemas.milestone import MilestoneCreate, MilestoneUpdate
from app.schemas.project import ProjectCreate, ProjectUpdate
from app.services.decision_service import DecisionService
from app.services.idea_service import IdeaService
from app.services.milestone_service import MilestoneService
from app.services.project_service import ProjectService
from app.services.user_service import UserService

DEFAULT_DATABASE_URL = "sqlite:///./demo.db"
DEMO_ACTIVE_LIMIT = 3


class SeedRefused(Exception):
    """The seed will not run against this target."""


@dataclass(frozen=True)
class ProjectSpec:
    name: str
    description: str
    status: ProjectStatus
    next_action: str | None
    milestones: tuple[str, ...]
    done: int
    decisions: tuple[tuple[str, str], ...] = ()
    # Days since the last activity; None leaves the value the services set (now)
    idle_days: int | None = None
    # With history: days ago each done milestone was completed, in milestone order. Never more
    # recent than idle_days, so last_activity_at stays coherent with the events
    done_days_ago: tuple[int, ...] = ()


LONG_NAME = "Plataforma de seguimiento de proyectos personales con bot de Telegram, panel web y exportación a Obsidian"
LONG_ACTION = (
    "Escribir el borrador del README con la arquitectura completa, los comandos del bot y los pasos para "
    "levantar el entorno local, y dejarlo listo para que otra persona pueda probarlo sin preguntarme nada"
)

PROJECTS: tuple[ProjectSpec, ...] = (
    ProjectSpec(
        LONG_NAME,
        "Registrar ideas y decisiones por proyecto y medir el avance real para no abandonar nada a medias.",
        ProjectStatus.ACTIVE,
        LONG_ACTION,
        ("Definir el modelo de datos", "Crear la API", "Conectar el bot", "Construir el panel"),
        0,
        (
            ("Calcular el porcentaje con hitos", "Si lo decide la IA o lo escribo a mano, deja de ser un dato fiable."),
            ("SQLite como fuente de verdad", "Corre en local y el vault de Obsidian solo es una exportación."),
        ),
        idle_days=3,
    ),
    ProjectSpec(
        "Curso de Rust",
        "Terminar el libro oficial y hacer un proyecto pequeño de línea de comandos.",
        ProjectStatus.ACTIVE,
        "Resolver los ejercicios del capítulo 10 sobre genéricos",
        ("Instalar el toolchain", "Capítulos 1 a 5", "Capítulos 6 a 9", "Proyecto minigrep", "Capítulos 10 a 13"),
        3,
        (("Estudiar por las mañanas", "Con la cabeza fresca avanzo el doble que de noche."),),
        idle_days=12,
        done_days_ago=(38, 19, 12),
    ),
    ProjectSpec(
        "Rediseño del portafolio",
        "Renovar el sitio personal con tres casos de estudio y un diseño más sobrio.",
        ProjectStatus.ACTIVE,
        "Revisar la ortografía de los textos antes de publicar",
        ("Elegir tipografía y paleta", "Escribir los tres casos de estudio", "Maquetar la portada", "Optimizar imágenes", "Publicar"),
        4,
        (
            ("Un solo caso por página", "Facilita leerlos en el móvil y compartirlos por separado."),
            ("Sin librería de animaciones", "Pesaba más que el resto del sitio junto."),
            ("Dominio actual sin cambios", "Evita perder el posicionamiento que ya tiene."),
        ),
        idle_days=1,
        done_days_ago=(24, 13, 6, 1),
    ),
    ProjectSpec(
        "Blog de cocina casera",
        "Recetas de la semana con fotos y costos aproximados.",
        ProjectStatus.PAUSED,
        "Fotografiar el guiso de lentejas con luz natural",
        ("Montar el blog", "Publicar cinco recetas", "Plantilla de fotos"),
        1,
        idle_days=47,
        done_days_ago=(50,),
    ),
    ProjectSpec(
        "Automatizar la facturación",
        "Generar y enviar las facturas mensuales sin copiar datos a mano.",
        ProjectStatus.IDEA,
        None,
        (),
        0,
    ),
    ProjectSpec(
        "App de recetas",
        "Guardar recetas y generar la lista de compras de la semana.",
        ProjectStatus.IDEA,
        None,
        ("Listar requisitos",),
        0,
        idle_days=20,
    ),
    ProjectSpec(
        "Huerto urbano en el balcón",
        "Sensores de humedad y riego automático con una placa económica.",
        ProjectStatus.PAUSED,
        "Comprar el sensor de humedad capacitivo",
        ("Probar el riego manual", "Comprar sensores", "Escribir el firmware"),
        1,
        (("Probar primero con una sola maceta", "Si falla, pierdo una planta y no todo el balcón."),),
        idle_days=18,
        done_days_ago=(22,),
    ),
    ProjectSpec(
        "Aprender guitarra",
        "Veinte minutos diarios hasta tocar tres canciones completas.",
        ProjectStatus.PAUSED,
        None,
        ("Afinar y acordes básicos", "Primera canción completa"),
        0,
        idle_days=9,
    ),
    ProjectSpec(
        "Migración del servidor casero",
        "Pasar los servicios del equipo viejo al nuevo con copias de seguridad verificadas.",
        ProjectStatus.DONE,
        None,
        ("Inventariar servicios", "Configurar las copias de seguridad", "Migrar los datos", "Apagar el equipo viejo"),
        4,
        (("Docker Compose en lugar de instalar a mano", "Se reproduce en una tarde si algo falla."),),
        idle_days=33,
        done_days_ago=(76, 58, 41, 33),
    ),
)

# (content, project name or None for the inbox)
IDEAS: tuple[tuple[str, str | None], ...] = (
    ("Explorar si Obsidian tiene una API para leer las propiedades del frontmatter", None),
    ("Probar un resumen semanal que llegue por Telegram los domingos", None),
    ("Comprar un dominio corto para los proyectos", None),
    (
        "Escribir un artículo contando por qué limito a tres los proyectos activos, con ejemplos de proyectos que abandoné"
        " y qué cambió desde que pongo una sola próxima acción por proyecto",
        None,
    ),
    ("Añadir modo oscuro automático según la hora", "Rediseño del portafolio"),
    ("Hacer un ejercicio semanal de lectura de código ajeno", "Curso de Rust"),
    ("Mostrar los días sin tocar en el bot", LONG_NAME),
    ("Preguntar a un amigo cocinero por sus trucos", "Blog de cocina casera"),
)


# (content, project name or None for the inbox, days ago captured, days ago assigned). Assignments are
# never more recent than the project's idle_days, so last_activity_at stays coherent.
HISTORY_IDEAS: tuple[tuple[str, str | None, int, int | None], ...] = (
    ("Revisar cómo exportan otros paneles sus datos a Markdown", None, 2, None),
    ("Probar un tablero de lectura para los artículos guardados", None, 9, None),
    ("Averiguar si el router casero soporta VLAN", None, 15, None),
    ("Hacer una lista de libros técnicos pendientes", None, 30, None),
    ("Medir cuánto tiempo real dedico a cada proyecto", None, 44, None),
    ("Grabar un video corto mostrando el flujo del bot", None, 52, None),
    ("Resolver los ejercicios de ownership antes del capítulo 5", "Curso de Rust", 40, 38),
    ("Escribir un CLI pequeño para renombrar archivos", "Curso de Rust", 26, 26),
    ("Probar una portada con una sola columna", "Rediseño del portafolio", 60, 55),
    ("Agregar una página de contacto sin formulario", "Rediseño del portafolio", 33, 30),
    ("Comprimir las capturas con un script", "Rediseño del portafolio", 14, 10),
    ("Elegir una foto de perfil nueva", "Rediseño del portafolio", 8, 3),
    ("Enviar un recordatorio si pasan cinco días sin tocar un proyecto", LONG_NAME, 21, 21),
    ("Mostrar las decisiones recientes en el panel", LONG_NAME, 11, 5),
    ("Permitir mover una idea de proyecto con un comando", LONG_NAME, 5, 4),
    ("Hacer una receta de pan con masa madre", "Blog de cocina casera", 80, 75),
    ("Anotar el costo por porción en cada receta", "Blog de cocina casera", 66, 66),
    ("Usar un higrómetro de suelo en vez de estimar el riego", "Huerto urbano en el balcón", 29, 22),
    ("Documentar el procedimiento de restauración de copias", "Migración del servidor casero", 77, 76),
    ("Practicar el cambio entre acordes con un metrónomo", "Aprender guitarra", 19, 12),
)


def target_url(cli_url: str | None) -> str:
    # Only the process environment, never the .env file, can name a different database
    return cli_url or os.environ.get("DATABASE_URL") or DEFAULT_DATABASE_URL


def check_target(url: str) -> None:
    parsed = make_url(url)
    if parsed.get_backend_name() != "sqlite" or not parsed.database:
        raise SeedRefused(f"Solo se siembran bases SQLite en archivo; recibí: {parsed.render_as_string()}")
    if "demo" not in Path(parsed.database).name.lower():
        raise SeedRefused(
            f"'{Path(parsed.database).name}' no parece una base de demo (el nombre debe incluir 'demo'). "
            "Usa DATABASE_URL=sqlite:///./demo.db"
        )


def _clear(session: Session, user_id: int, settings: Settings) -> None:
    projects = ProjectService(session, user_id, settings)
    for project in projects.list():
        projects.delete(project.id)
    ideas = IdeaService(session, user_id)
    for idea in ideas.list_all():
        ideas.delete(idea.id)


def _backdate(session: Session, project_id: int, days: int) -> None:
    # Services always stamp "now"; the only way to show stale projects is to move the timestamp back
    session.get(Project, project_id).last_activity_at = utcnow() - timedelta(days=days)


def _apply_history(session: Session, user_id: int, ids: dict[str, int]) -> None:
    """Moves events back in time so the metrics have weeks to show. Services only stamp "now"."""
    now = utcnow()
    projects = {spec.name: spec for spec in PROJECTS}

    for name, spec in projects.items():
        done = session.scalars(
            select(Milestone)
            .where(Milestone.project_id == ids[name], Milestone.done.is_(True))
            .order_by(Milestone.position)
        ).all()
        for milestone, days in zip(done, spec.done_days_ago, strict=True):
            milestone.completed_at = now - timedelta(days=days)
            milestone.created_at = milestone.completed_at - timedelta(days=1)

    ideas = IdeaService(session, user_id)
    # The base ideas that sit in a project take the project's last activity as their moment
    for idea in session.scalars(select(Idea).where(Idea.user_id == user_id, Idea.project_id.is_not(None))):
        idle = next(s.idle_days for s in PROJECTS if ids[s.name] == idea.project_id)
        idea.created_at = idea.assigned_at = now - timedelta(days=idle or 0)

    for content, project_name, captured, assigned in HISTORY_IDEAS:
        idea = ideas.create(IdeaCreate(content=content, project_id=ids[project_name] if project_name else None))
        idea.created_at = now - timedelta(days=captured)
        idea.assigned_at = now - timedelta(days=assigned) if assigned is not None else None

    # Projects start before their first event
    for name, spec in projects.items():
        if spec.done_days_ago:
            session.get(Project, ids[name]).created_at = now - timedelta(days=max(spec.done_days_ago) + 14)
    session.commit()


def seed(session: Session, settings: Settings, *, reset: bool, history: bool = True) -> list:
    user = UserService.get_or_create_user(session, settings.telegram_allowed_user_id)
    has_data = session.scalar(select(Project.id).where(Project.user_id == user.id).limit(1)) is not None
    has_data = has_data or session.scalar(select(Idea.id).where(Idea.user_id == user.id).limit(1)) is not None
    if has_data and not reset:
        raise SeedRefused("La base ya tiene datos. Usa --reset para borrarlos y volver a sembrar.")
    # The limit is part of the demo scenario, whatever MAX_ACTIVE_PROJECTS says in the environment
    settings = settings.model_copy(update={"max_active_projects": DEMO_ACTIVE_LIMIT})
    if has_data:
        _clear(session, user.id, settings)

    projects = ProjectService(session, user.id, settings)
    milestones = MilestoneService(session, user.id)
    decisions = DecisionService(session, user.id)
    ideas = IdeaService(session, user.id)

    ids: dict[str, int] = {}
    for spec in PROJECTS:
        project = projects.create(ProjectCreate(name=spec.name, description=spec.description))
        ids[spec.name] = project.id
        created = [milestones.create(project.id, MilestoneCreate(title=title)) for title in spec.milestones]
        for milestone in created[: spec.done]:
            milestones.update(milestone.id, MilestoneUpdate(done=True))
        for title, rationale in spec.decisions:
            decisions.create(project.id, DecisionCreate(title=title, rationale=rationale))
        # Active first so the limit is enforced by the service, not by this script
        if spec.status is not ProjectStatus.IDEA:
            projects.update(project.id, ProjectUpdate(status=spec.status, next_action=spec.next_action))

    for content, project_name in IDEAS:
        ideas.create(IdeaCreate(content=content, project_id=ids[project_name] if project_name else None))

    if history:
        _apply_history(session, user.id, ids)

    for spec in PROJECTS:
        if spec.idle_days is not None:
            _backdate(session, ids[spec.name], spec.idle_days)
    session.commit()
    return projects.list()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Siembra datos de demo en una base aparte.")
    parser.add_argument("--reset", action="store_true", help="borra los datos de la base de demo antes de sembrar")
    parser.add_argument("--no-history", action="store_true", help="solo el conjunto base, sin hitos ni ideas con historia")
    parser.add_argument("--database-url", help=f"por defecto DATABASE_URL del entorno o {DEFAULT_DATABASE_URL}")
    args = parser.parse_args(argv)

    url = target_url(args.database_url)
    try:
        check_target(url)
        engine = create_engine(url)
        if "projects" not in inspect(engine).get_table_names():
            raise SeedRefused("La base no tiene tablas. Ejecuta antes: alembic upgrade head")
        with Session(engine, expire_on_commit=False) as session:
            result = seed(session, Settings(), reset=args.reset, history=not args.no_history)
            idea_count = session.scalar(select(func.count()).select_from(Idea))
            done_count = session.scalar(select(func.count()).select_from(Milestone).where(Milestone.done.is_(True)))
    except SeedRefused as error:
        print(f"Seed cancelado: {error}", file=sys.stderr)
        return 1

    by_status: dict[str, int] = {}
    for project in result:
        by_status[project.status.value] = by_status.get(project.status.value, 0) + 1
    print(f"Base de demo lista ({make_url(url).database}): {len(result)} proyectos {by_status}, {idea_count} ideas, {done_count} hitos hechos.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
