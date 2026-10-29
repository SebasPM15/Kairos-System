from fastapi import APIRouter

from app.bot.catalog import COMMAND_CATALOG, CommandInfo

router = APIRouter(tags=["bot"])


@router.get("/bot/commands", response_model=list[CommandInfo])
def list_bot_commands():
    return COMMAND_CATALOG
