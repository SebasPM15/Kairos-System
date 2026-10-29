from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import User


class UserService:
    @staticmethod
    def get_or_create_user(session: Session, telegram_id: int | None) -> User:
        """telegram_id None is the local default user."""
        user = session.scalar(select(User).where(User.telegram_id == telegram_id))
        if user is None:
            user = User(telegram_id=telegram_id)
            session.add(user)
            session.commit()
        return user
