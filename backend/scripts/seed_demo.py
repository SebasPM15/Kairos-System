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

from sqlalchemy import create_engine, inspect, select
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from app.config import Settings
from app.models import Idea, Project, ProjectStatus
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
    ),
    ProjectSpec(
        "Blog de cocina casera",
        "Recetas de la semana con fotos y costos aproximados.",
        ProjectStatus.PAUSED,
        "Fotografiar el guiso de lentejas con luz natural",
        ("Montar el blog", "Publicar cinco recetas", "Plantilla de fotos"),
        1,
        idle_days=47,
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


def seed(session: Session, settings: Settings, *, reset: bool) -> list:
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

    for spec in PROJECTS:
        if spec.idle_days is not None:
            _backdate(session, ids[spec.name], spec.idle_days)
    session.commit()
    return projects.list()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Siembra datos de demo en una base aparte.")
    parser.add_argument("--reset", action="store_true", help="borra los datos de la base de demo antes de sembrar")
    parser.add_argument("--database-url", help=f"por defecto DATABASE_URL del entorno o {DEFAULT_DATABASE_URL}")
    args = parser.parse_args(argv)

    url = target_url(args.database_url)
    try:
        check_target(url)
        engine = create_engine(url)
        if "projects" not in inspect(engine).get_table_names():
            raise SeedRefused("La base no tiene tablas. Ejecuta antes: alembic upgrade head")
        with Session(engine, expire_on_commit=False) as session:
            result = seed(session, Settings(), reset=args.reset)
    except SeedRefused as error:
        print(f"Seed cancelado: {error}", file=sys.stderr)
        return 1

    by_status: dict[str, int] = {}
    for project in result:
        by_status[project.status.value] = by_status.get(project.status.value, 0) + 1
    print(f"Base de demo lista ({make_url(url).database}): {len(result)} proyectos {by_status}, {len(IDEAS)} ideas.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
