"""Single source of truth for the bot's commands: help text, Telegram menu and GET /bot/commands."""

from pydantic import BaseModel, computed_field


class CommandInfo(BaseModel):
    name: str
    # Arguments as typed after the command, empty when it takes none
    args: str = ""
    description: str

    @computed_field
    @property
    def syntax(self) -> str:
        return f"/{self.name} {self.args}".strip()


COMMAND_CATALOG: tuple[CommandInfo, ...] = (
    CommandInfo(name="proyecto", args="<nombre>", description="Crea un proyecto en estado idea"),
    CommandInfo(name="idea", args="[slug:] <texto>", description="Guarda una idea en un proyecto o en la bandeja"),
    CommandInfo(name="hito", args="<slug>: <título>", description="Agrega un hito a un proyecto"),
    CommandInfo(name="hecho", args="[id]", description="Marca un hito como hecho"),
    CommandInfo(name="estado", args="[slug]", description="Muestra tus proyectos o el detalle de uno"),
    CommandInfo(name="foco", args="<slug>: <próxima acción>", description="Activa un proyecto y fija su próxima acción"),
    CommandInfo(name="decision", args="<slug>: <título> | <porqué>", description="Registra una decisión con su razón"),
    CommandInfo(name="pausa", args="<slug>", description="Pausa un proyecto y libera un cupo de activos"),
    CommandInfo(name="terminar", args="<slug>", description="Marca un proyecto como terminado"),
    CommandInfo(name="exportar", description="Exporta tus proyectos al vault de Obsidian"),
    CommandInfo(name="ayuda", description="Muestra los comandos disponibles"),
)


def help_text() -> str:
    lines = ["Comandos:"]
    lines.extend(f"{command.syntax} - {command.description}" for command in COMMAND_CATALOG)
    return "\n".join(lines)
