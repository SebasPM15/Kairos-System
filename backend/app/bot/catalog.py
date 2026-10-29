"""Single source of truth for the bot's commands: help text, Telegram menu and GET /bot/commands."""

from pydantic import BaseModel


class CommandInfo(BaseModel):
    name: str
    syntax: str
    description: str


COMMAND_CATALOG: tuple[CommandInfo, ...] = (
    CommandInfo(name="proyecto", syntax="/proyecto <nombre>", description="Crea un proyecto en estado idea"),
    CommandInfo(name="idea", syntax="/idea [slug:] <texto>", description="Guarda una idea en un proyecto o en la bandeja"),
    CommandInfo(name="hito", syntax="/hito <slug>: <título>", description="Agrega un hito a un proyecto"),
    CommandInfo(name="hecho", syntax="/hecho [id]", description="Marca un hito como hecho"),
    CommandInfo(name="estado", syntax="/estado [slug]", description="Muestra tus proyectos o el detalle de uno"),
    CommandInfo(name="foco", syntax="/foco <slug>: <próxima acción>", description="Activa un proyecto y fija su próxima acción"),
    CommandInfo(name="decision", syntax="/decision <slug>: <título> | <porqué>", description="Registra una decisión con su razón"),
    CommandInfo(name="pausa", syntax="/pausa <slug>", description="Pausa un proyecto y libera un cupo de activos"),
    CommandInfo(name="terminar", syntax="/terminar <slug>", description="Marca un proyecto como terminado"),
    CommandInfo(name="exportar", syntax="/exportar", description="Exporta tus proyectos al vault de Obsidian"),
    CommandInfo(name="ayuda", syntax="/ayuda", description="Muestra los comandos disponibles"),
)


def help_text() -> str:
    lines = ["Comandos:"]
    lines.extend(f"{command.syntax} - {command.description}" for command in COMMAND_CATALOG)
    return "\n".join(lines)
