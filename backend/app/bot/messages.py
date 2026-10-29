"""Spanish texts of the bot and the single mapping from domain errors to messages."""

from app.models import ProjectStatus
from app.services import errors

STATUS_LABELS = {
    ProjectStatus.IDEA: "idea",
    ProjectStatus.ACTIVE: "activo",
    ProjectStatus.PAUSED: "pausa",
    ProjectStatus.DONE: "terminado",
}

USAGE = {
    "proyecto": "Uso: /proyecto <nombre>",
    "idea": "Uso: /idea [slug:] <texto>",
    "hito": "Uso: /hito <slug>: <título>",
    "hecho": "Uso: /hecho <id>",
    "foco": "Uso: /foco <slug>: <próxima acción>",
    "decision": "Uso: /decision <slug>: <título> | <porqué>",
    "pausa": "Uso: /pausa <slug>",
    "terminar": "Uso: /terminar <slug>",
}

HELP = "\n".join(
    [
        "Comandos:",
        "/proyecto <nombre>",
        "/idea [slug:] <texto>",
        "/hito <slug>: <título>",
        "/hecho [id]",
        "/estado [slug]",
        "/foco <slug>: <próxima acción>",
        "/decision <slug>: <título> | <porqué>",
        "/pausa <slug>",
        "/terminar <slug>",
        "/ayuda",
    ]
)


def all_milestones_done(slug: str) -> str:
    return f"Todos los hitos de {slug} están hechos. Usa /terminar {slug} o agrega más hitos con /hito."

NO_PROJECTS = "Aún no tienes proyectos. Crea uno con /proyecto <nombre>."
NO_PENDING_MILESTONES = "No tienes hitos pendientes."
PICK_MILESTONE = "¿Qué hito terminaste?"
INVALID_INPUT = "El texto es inválido o demasiado largo."
UNEXPECTED_ERROR = "Algo salió mal. Intenta de nuevo."

_DOMAIN_MESSAGES = {
    errors.ProjectNotFound: lambda e: "No existe ese proyecto. Usa /estado para ver tus proyectos.",
    errors.MilestoneNotFound: lambda e: "No existe ese hito. Usa /estado <slug> para ver sus IDs.",
    errors.IdeaNotFound: lambda e: "No existe esa idea.",
    errors.DecisionNotFound: lambda e: "No existe esa decisión.",
    errors.ActiveLimitReached: lambda e: (
        f"Límite de {e.args[0]} proyectos activos alcanzado. "
        "Pausa o termina uno antes de activar otro."
    ),
    errors.NextActionRequired: lambda e: "Un proyecto activo necesita una próxima acción.",
}


def error_message(error: Exception) -> str:
    """Message for a domain error; subclasses fall back to their closest mapped parent."""
    for cls in type(error).__mro__:
        if cls in _DOMAIN_MESSAGES:
            return _DOMAIN_MESSAGES[cls](error)
    return UNEXPECTED_ERROR


def days_label(days: int) -> str:
    if days <= 0:
        return "tocado hoy"
    return f"{days} día sin tocar" if days == 1 else f"{days} días sin tocar"
