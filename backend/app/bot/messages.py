"""Spanish texts of the bot and the single mapping from domain errors to messages."""

from datetime import datetime
from zoneinfo import ZoneInfo

from app.bot.catalog import help_text
from app.models import ProjectStatus, ReminderKind
from app.schemas.export import ExportSummary
from app.schemas.reminder import ReminderAlert, RemindersRead
from app.services import errors
from app.services.reminder_digest import Digest

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
    "posponer": "Uso: /posponer <slug>: <días> (de 1 a 30)",
    "silenciar": "Uso: /silenciar <slug>",
    "reactivar": "Uso: /reactivar <slug>",
}

HELP = help_text()


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
    errors.VaultNotConfigured: lambda e: (
        "El vault de Obsidian no está configurado. "
        "Define OBSIDIAN_VAULT_PATH con una carpeta que exista."
    ),
    errors.UnsafeVaultPath: lambda e: "Una ruta del export queda fuera del vault; no se escribió nada.",
}


def error_message(error: Exception) -> str:
    """Message for a domain error; subclasses fall back to their closest mapped parent."""
    for cls in type(error).__mro__:
        if cls in _DOMAIN_MESSAGES:
            return _DOMAIN_MESSAGES[cls](error)
    return UNEXPECTED_ERROR


def export_summary(summary: ExportSummary) -> str:
    projects = "proyecto" if summary.projects_exported == 1 else "proyectos"
    lines = [
        f"Export listo: {summary.projects_exported} {projects}, "
        f"{summary.files_written} archivos escritos, {summary.files_unchanged} sin cambios."
    ]
    if summary.orphans:
        lines.append(f"Carpetas huérfanas (no se tocaron): {', '.join(summary.orphans)}")
    return "\n".join(lines)


def days_label(days: int) -> str:
    if days <= 0:
        return "tocado hoy"
    return f"{days} día sin tocar" if days == 1 else f"{days} días sin tocar"


MAX_NEXT_ACTION_LENGTH = 140


def idle_label(days: int) -> str:
    return f"{days} día sin avance" if days == 1 else f"{days} días sin avance"


def alert_line(alert: ReminderAlert) -> str:
    """One alert as a sentence; shared by the digest and /recordatorios."""
    if alert.kind is ReminderKind.READY_TO_FINISH:
        return (
            f"{alert.slug}: todos los hitos están hechos. "
            f"Usa /terminar {alert.slug} o agrega más con /hito."
        )
    line = f"{alert.slug}: {idle_label(alert.days_idle)}."
    if alert.milestones_total == 0:
        line += " Aún no tiene hitos."
    if alert.next_action:
        action = alert.next_action
        if len(action) > MAX_NEXT_ACTION_LENGTH:
            action = action[: MAX_NEXT_ACTION_LENGTH - 1] + "…"
        line += f" Próxima acción: {action}"
    return line


def paused_summary(count: int, days: int) -> str:
    if count == 1:
        return f"Y 1 proyecto en pausa lleva más de {days} días: /recordatorios"
    return f"Y {count} proyectos en pausa llevan más de {days} días: /recordatorios"


def digest_text(digest: Digest, stale_days_paused: int) -> str:
    lines = ["Recordatorios"]
    lines += [f"{n}. {alert_line(alert)}" for n, alert in enumerate(digest.items, start=1)]
    if digest.overflow:
        lines.append(f"Hay {digest.overflow} más en /recordatorios.")
    if digest.paused:
        lines.append(paused_summary(len(digest.paused), stale_days_paused))
    return "\n".join(lines)


NO_REMINDERS = "No hay recordatorios pendientes. Tus proyectos tienen actividad reciente."
INVALID_SNOOZE_DAYS = "Indica un número de días entre 1 y 30."


def short_date(moment: datetime, tz: ZoneInfo) -> str:
    return moment.astimezone(tz).strftime("%d/%m")


def days_phrase(days: int) -> str:
    return "1 día" if days == 1 else f"{days} días"


def reminders_text(overview: RemindersRead, tz: ZoneInfo) -> str:
    """Everything /recordatorios shows: live alerts plus the projects that are snoozed or muted."""
    if not overview.alerts and not overview.suppressed:
        return NO_REMINDERS
    lines = ["Recordatorios"] if overview.alerts else ["No hay recordatorios pendientes."]
    lines += [f"{n}. {alert_line(alert)}" for n, alert in enumerate(overview.alerts, start=1)]
    if overview.suppressed:
        lines.append("Pospuestos o silenciados:")
        for item in overview.suppressed:
            state = "silenciado" if item.muted else f"pospuesto hasta el {short_date(item.snoozed_until, tz)}"
            lines.append(f"- {item.slug}: {state}")
        lines.append("Usa /reactivar <slug> para volver a recibirlos.")
    return "\n".join(lines)
