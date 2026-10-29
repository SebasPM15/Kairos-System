from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db
from app.models import User


def get_current_user(db: Session = Depends(get_db)) -> User:
    """Single-user mode: the allowed Telegram user, or the local default user.

    The only place to replace with real authentication.
    """
    telegram_id = get_settings().telegram_allowed_user_id
    user = db.scalar(select(User).where(User.telegram_id == telegram_id))
    if user is None:
        user = User(telegram_id=telegram_id)
        db.add(user)
        db.commit()
    return user
