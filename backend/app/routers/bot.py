from fastapi import APIRouter, Request

from app.bot.catalog import COMMAND_CATALOG, CommandInfo
from app.bot.status import BotStatus
from app.schemas.bot import BotStatusRead

router = APIRouter(tags=["bot"])


@router.get("/bot/commands", response_model=list[CommandInfo])
def list_bot_commands():
    return COMMAND_CATALOG


@router.get("/bot/status", response_model=BotStatusRead)
def read_bot_status(request: Request):
    # Process-wide state of the single bot, not user data: no auth, like /health and /config
    status: BotStatus = request.app.state.bot_status
    return status.snapshot
