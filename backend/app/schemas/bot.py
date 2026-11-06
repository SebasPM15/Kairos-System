from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.bot.status import BotState


class LastErrorRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    type: str
    at: datetime


class BotStatusRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    status: BotState
    # A code or an exception class name; never a message, URL or token
    reason: str | None
    started_at: datetime | None
    last_message_sent_at: datetime | None
    last_error: LastErrorRead | None
