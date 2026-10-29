import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

import app.models  # noqa: F401  (registers tables on Base.metadata)
from app.config import Settings, get_settings
from app.db import Base, get_db
from app.deps import get_current_user
from app.main import create_app
from app.models import User


@pytest.fixture
def session(tmp_path):
    # check_same_thread off: TestClient runs endpoints in a worker thread
    engine = create_engine(
        f"sqlite:///{tmp_path / 'test.db'}", connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(engine)
    with Session(engine) as s:
        yield s
    engine.dispose()


@pytest.fixture
def users(session):
    users = [User(), User(telegram_id=2)]
    session.add_all(users)
    session.commit()
    return users


@pytest.fixture
def client(session, users):
    app = create_app()
    current = {"user": users[0]}
    app.dependency_overrides[get_db] = lambda: session
    app.dependency_overrides[get_current_user] = lambda: current["user"]
    app.dependency_overrides[get_settings] = lambda: Settings(max_active_projects=2)
    test_client = TestClient(app)
    test_client.as_user = lambda user: current.update(user=user)
    return test_client
