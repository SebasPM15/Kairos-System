from fastapi import Depends
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db
from app.models import User
from app.services.user_service import UserService


def get_current_user(db: Session = Depends(get_db)) -> User:
    """Single-user mode: the allowed Telegram user, or the local default user.

    The only place to replace with real authentication.
    """
    return UserService.get_or_create_user(db, get_settings().telegram_allowed_user_id)
