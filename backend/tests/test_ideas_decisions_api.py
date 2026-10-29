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


def foreign_project(client, users):
    client.as_user(users[1])
    created = client.post("/projects", json={"name": "Other"}).json()
    client.as_user(users[0])
    return created


def post_idea(client, **body):
    response = client.post("/ideas", json={"content": "idea", **body})
    assert response.status_code == 201
    return response.json()


def test_create_idea_in_inbox_and_project(client, project):
    inbox = post_idea(client)
    scoped = client.post(f"/projects/{project['id']}/ideas", json={"content": "scoped"})
    by_body = post_idea(client, project_id=project["id"])

    assert inbox["project_id"] is None
    assert scoped.status_code == 201 and scoped.json()["project_id"] == project["id"]
    assert by_body["project_id"] == project["id"]
    assert [i["id"] for i in client.get("/ideas").json()] == [inbox["id"]]
    listed = client.get(f"/projects/{project['id']}/ideas").json()
    assert [i["id"] for i in listed] == [scoped.json()["id"], by_body["id"]]


def test_idea_validation_is_422(client, project):
    assert client.post("/ideas", json={"content": ""}).status_code == 422
    assert client.post("/ideas", json={"content": "   "}).status_code == 422
    assert client.post("/ideas", json={}).status_code == 422
    idea = post_idea(client)
    assert client.patch(f"/ideas/{idea['id']}", json={"content": None}).status_code == 422
    assert client.patch(f"/ideas/{idea['id']}", json={"content": ""}).status_code == 422


def test_assign_and_unassign(client, project):
    idea = post_idea(client)

    assigned = client.patch(f"/ideas/{idea['id']}", json={"project_id": project["id"]})
    assert assigned.status_code == 200 and assigned.json()["project_id"] == project["id"]
    assert client.get("/ideas").json() == []

    back = client.patch(f"/ideas/{idea['id']}", json={"project_id": None})
    assert back.json()["project_id"] is None
    assert len(client.get("/ideas").json()) == 1


def test_patch_absent_vs_null(client, project):
    idea = post_idea(client, project_id=project["id"])

    edited = client.patch(f"/ideas/{idea['id']}", json={"content": "new"}).json()
    assert (edited["content"], edited["project_id"]) == ("new", project["id"])

    nulled = client.patch(f"/ideas/{idea['id']}", json={"project_id": None}).json()
    assert (nulled["content"], nulled["project_id"]) == ("new", None)


def test_assign_to_foreign_project_is_404(client, users):
    other = foreign_project(client, users)
    idea = post_idea(client)

    assert client.patch(f"/ideas/{idea['id']}", json={"project_id": other["id"]}).status_code == 404
    assert client.post("/ideas", json={"content": "x", "project_id": other["id"]}).status_code == 404
    assert client.post(f"/projects/{other['id']}/ideas", json={"content": "x"}).status_code == 404
    assert client.get(f"/projects/{other['id']}/ideas").status_code == 404


def test_last_activity_rule(client, project):
    def activity():
        return client.get(f"/projects/{project['id']}").json()["last_activity_at"]

    start = activity()
    inbox = post_idea(client)
    assert activity() == start

    client.patch(f"/ideas/{inbox['id']}", json={"project_id": project["id"]})
    assigned = activity()
    assert assigned > start

    client.patch(f"/ideas/{inbox['id']}", json={"project_id": None})
    assert activity() == assigned

    client.patch(f"/ideas/{inbox['id']}", json={"project_id": project["id"]})
    after_reassign = activity()
    client.delete(f"/ideas/{inbox['id']}")
    assert activity() == after_reassign

    post_idea(client, project_id=project["id"])
    assert activity() > after_reassign


def test_delete_idea_and_unknown_is_404(client):
    idea = post_idea(client)

    assert client.delete(f"/ideas/{idea['id']}").status_code == 204
    assert client.delete(f"/ideas/{idea['id']}").status_code == 404
    assert client.patch("/ideas/999", json={"content": "x"}).status_code == 404


def test_ideas_isolated_between_users(client, users, project):
    mine = post_idea(client, project_id=project["id"])
    inbox = post_idea(client)

    client.as_user(users[1])
    assert client.get("/ideas").json() == []
    assert client.get(f"/projects/{project['id']}/ideas").status_code == 404
    assert client.patch(f"/ideas/{mine['id']}", json={"content": "x"}).status_code == 404
    assert client.delete(f"/ideas/{inbox['id']}").status_code == 404

    client.as_user(users[0])
    assert len(client.get("/ideas").json()) == 1


def test_deleting_project_leaves_ideas_in_inbox(client, project):
    idea = post_idea(client, project_id=project["id"])

    assert client.delete(f"/projects/{project['id']}").status_code == 204

    inbox = client.get("/ideas").json()
    assert [(i["id"], i["project_id"]) for i in inbox] == [(idea["id"], None)]


def test_decision_crud(client, project):
    url = f"/projects/{project['id']}/decisions"

    created = client.post(url, json={"title": "SQLite", "rationale": "Local only"})
    assert created.status_code == 201
    decision = created.json()
    assert (decision["title"], decision["rationale"]) == ("SQLite", "Local only")
    assert client.get(url).json() == [decision]

    assert client.delete(f"/decisions/{decision['id']}").status_code == 204
    assert client.get(url).json() == []
    assert client.delete(f"/decisions/{decision['id']}").status_code == 404


@pytest.mark.parametrize(
    "body",
    [{"title": "x"}, {"title": "x", "rationale": ""}, {"title": "", "rationale": "y"}, {}],
)
def test_decision_validation_is_422(client, project, body):
    response = client.post(f"/projects/{project['id']}/decisions", json=body)

    assert response.status_code == 422


def test_decision_updates_last_activity(client, project):
    before = client.get(f"/projects/{project['id']}").json()["last_activity_at"]

    client.post(f"/projects/{project['id']}/decisions", json={"title": "t", "rationale": "r"})

    assert client.get(f"/projects/{project['id']}").json()["last_activity_at"] > before


def test_decisions_isolated_between_users(client, users, project):
    url = f"/projects/{project['id']}/decisions"
    decision = client.post(url, json={"title": "t", "rationale": "r"}).json()

    client.as_user(users[1])
    assert client.get(url).status_code == 404
    assert client.post(url, json={"title": "t", "rationale": "r"}).status_code == 404
    assert client.delete(f"/decisions/{decision['id']}").status_code == 404

    client.as_user(users[0])
    assert len(client.get(url).json()) == 1


def test_deleting_project_deletes_decisions(client, project):
    decision = client.post(
        f"/projects/{project['id']}/decisions", json={"title": "t", "rationale": "r"}
    ).json()

    client.delete(f"/projects/{project['id']}")

    assert client.delete(f"/decisions/{decision['id']}").status_code == 404
