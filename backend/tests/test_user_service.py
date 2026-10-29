import pytest
from sqlalchemy import select

from app.models import User
from app.services.user_service import UserService


@pytest.mark.parametrize("telegram_id", [None, 5_000_000_000])
def test_creates_the_user_once(session, telegram_id):
    first = UserService.get_or_create_user(session, telegram_id)
    second = UserService.get_or_create_user(session, telegram_id)

    assert first.id == second.id
    assert first.telegram_id == telegram_id
    assert len(session.scalars(select(User)).all()) == 1


def test_different_telegram_ids_are_different_users(session):
    a = UserService.get_or_create_user(session, 1)
    b = UserService.get_or_create_user(session, 2)

    assert a.id != b.id
