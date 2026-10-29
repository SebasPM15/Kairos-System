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
    app.dependency_overrides[get_settings] = lambda: Settings(max_active_projects=1)
    test_client = TestClient(app)
    test_client.as_user = lambda user: current.update(user=user)
    return test_client


def create(client, name="Kairos"):
    response = client.post("/projects", json={"name": name})
    assert response.status_code == 201
    return response.json()


def test_create_and_read(client):
    created = create(client)

    assert created["slug"] == "kairos"
    assert created["status"] == "idea"
    assert created["days_since_activity"] == 0
    assert client.get(f"/projects/{created['id']}").json() == created
    assert client.get("/projects").json() == [created]


def test_duplicate_name_gets_suffix(client):
    create(client)

    assert create(client)["slug"] == "kairos-2"


def test_create_rejects_empty_name(client):
    assert client.post("/projects", json={"name": ""}).status_code == 422


def test_activate_without_next_action_is_422(client):
    project = create(client)

    response = client.patch(f"/projects/{project['id']}", json={"status": "active"})

    assert response.status_code == 422


def test_activate_with_limit_reached_is_409(client):
    first, second = create(client, "A"), create(client, "B")
    body = {"status": "active", "next_action": "go"}
    assert client.patch(f"/projects/{first['id']}", json=body).status_code == 200

    response = client.patch(f"/projects/{second['id']}", json=body)

    assert response.status_code == 409


def test_reactivate_active_project_with_full_limit(client):
    project = create(client)
    url = f"/projects/{project['id']}"
    client.patch(url, json={"status": "active", "next_action": "go"})

    response = client.patch(url, json={"status": "active", "next_action": "go again"})

    assert response.status_code == 200
    assert response.json()["next_action"] == "go again"


def test_pause_keeps_next_action(client):
    project = create(client)
    url = f"/projects/{project['id']}"
    client.patch(url, json={"status": "active", "next_action": "go"})

    body = client.patch(url, json={"status": "paused"}).json()

    assert body["status"] == "paused"
    assert body["next_action"] == "go"


def test_invalid_status_is_422(client):
    project = create(client)

    assert client.patch(f"/projects/{project['id']}", json={"status": "bogus"}).status_code == 422


def test_delete_then_404(client):
    project = create(client)
    url = f"/projects/{project['id']}"

    assert client.delete(url).status_code == 204
    assert client.get(url).status_code == 404
    assert client.delete(url).status_code == 404


def test_other_user_cannot_see_or_touch_project(client, users):
    project = create(client)
    client.as_user(users[1])
    url = f"/projects/{project['id']}"

    assert client.get("/projects").json() == []
    assert client.get(url).status_code == 404
    assert client.patch(url, json={"name": "x"}).status_code == 404
    assert client.delete(url).status_code == 404
