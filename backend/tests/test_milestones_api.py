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
    app.dependency_overrides[get_settings] = lambda: Settings()
    test_client = TestClient(app)
    test_client.as_user = lambda user: current.update(user=user)
    return test_client


@pytest.fixture
def project(client):
    return client.post("/projects", json={"name": "Kairos"}).json()


def add(client, project, title="step"):
    response = client.post(f"/projects/{project['id']}/milestones", json={"title": title})
    assert response.status_code == 201
    return response.json()


def progress(client, project):
    body = client.get(f"/projects/{project['id']}").json()
    return body["progress"], body["milestones_done"], body["milestones_total"]


def test_project_without_milestones_has_zero_progress(client, project):
    assert project["progress"] == 0
    assert (project["milestones_done"], project["milestones_total"]) == (0, 0)


def test_create_and_list_in_order(client, project):
    first, second = add(client, project, "a"), add(client, project, "b")

    listed = client.get(f"/projects/{project['id']}/milestones").json()

    assert (first["position"], second["position"]) == (0, 1)
    assert [m["title"] for m in listed] == ["a", "b"]
    assert listed[0]["done"] is False and listed[0]["completed_at"] is None


def test_progress_follows_done_reopen_and_delete(client, project):
    a, b = add(client, project, "a"), add(client, project, "b")

    done = client.patch(f"/milestones/{a['id']}", json={"done": True}).json()
    assert done["completed_at"] is not None
    assert progress(client, project) == (50, 1, 2)

    client.patch(f"/milestones/{b['id']}", json={"done": True})
    assert progress(client, project) == (100, 2, 2)

    reopened = client.patch(f"/milestones/{b['id']}", json={"done": False}).json()
    assert reopened["completed_at"] is None
    assert progress(client, project) == (50, 1, 2)

    assert client.delete(f"/milestones/{b['id']}").status_code == 204
    assert progress(client, project) == (100, 1, 1)
    assert client.get("/projects").json()[0]["progress"] == 100


def test_reorder_via_patch(client, project):
    add(client, project, "a")
    b = add(client, project, "b")

    client.patch(f"/milestones/{b['id']}", json={"position": 0})

    listed = client.get(f"/projects/{project['id']}/milestones").json()
    assert [(m["title"], m["position"]) for m in listed] == [("b", 0), ("a", 1)]


def test_validation_errors_are_422(client, project):
    milestone = add(client, project)
    url = f"/projects/{project['id']}/milestones"

    assert client.post(url, json={"title": ""}).status_code == 422
    assert client.patch(f"/milestones/{milestone['id']}", json={"position": -1}).status_code == 422
    assert client.patch(f"/milestones/{milestone['id']}", json={"title": ""}).status_code == 422


def test_unknown_ids_are_404(client):
    assert client.get("/projects/999/milestones").status_code == 404
    assert client.post("/projects/999/milestones", json={"title": "x"}).status_code == 404
    assert client.patch("/milestones/999", json={"done": True}).status_code == 404
    assert client.delete("/milestones/999").status_code == 404


def test_other_user_gets_404_everywhere(client, users, project):
    milestone = add(client, project)
    client.as_user(users[1])
    url = f"/projects/{project['id']}/milestones"

    assert client.get(url).status_code == 404
    assert client.post(url, json={"title": "x"}).status_code == 404
    assert client.patch(f"/milestones/{milestone['id']}", json={"done": True}).status_code == 404
    assert client.delete(f"/milestones/{milestone['id']}").status_code == 404

    client.as_user(users[0])
    assert progress(client, project) == (0, 0, 1)
