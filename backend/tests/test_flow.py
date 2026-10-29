from datetime import timedelta

from app.models import Project
from app.models.base import utcnow


def backdate(session, project_id, days):
    project = session.get(Project, project_id)
    project.last_activity_at = utcnow() - timedelta(days=days)
    session.commit()


def get_project(client, project_id):
    return client.get(f"/projects/{project_id}").json()


def test_full_project_lifecycle(client, session):
    project = client.post("/projects", json={"name": "Kairos"}).json()
    pid = project["id"]
    assert (project["status"], project["progress"], project["milestones_total"]) == ("idea", 0, 0)

    first = client.post(f"/projects/{pid}/milestones", json={"title": "API"}).json()
    client.post(f"/projects/{pid}/milestones", json={"title": "Bot"})
    assert get_project(client, pid)["milestones_total"] == 2

    backdate(session, pid, days=5)
    assert get_project(client, pid)["days_since_activity"] == 5

    client.patch(f"/milestones/{first['id']}", json={"done": True})
    after_milestone = get_project(client, pid)
    assert after_milestone["progress"] == 50
    assert after_milestone["milestones_done"] == 1
    assert after_milestone["days_since_activity"] == 0

    backdate(session, pid, days=3)
    client.post(f"/projects/{pid}/ideas", json={"content": "Weekly summary"})
    assert get_project(client, pid)["days_since_activity"] == 0

    backdate(session, pid, days=2)
    client.post(f"/projects/{pid}/decisions", json={"title": "SQLite", "rationale": "Local only"})
    assert get_project(client, pid)["days_since_activity"] == 0

    backdate(session, pid, days=1)
    activated = client.patch(
        f"/projects/{pid}", json={"status": "active", "next_action": "Write tests"}
    )
    assert activated.status_code == 200
    body = activated.json()
    assert body["status"] == "active"
    assert body["next_action"] == "Write tests"
    assert body["progress"] == 50
    assert body["days_since_activity"] == 0

    ideas = client.get(f"/projects/{pid}/ideas").json()
    assert [i["content"] for i in ideas] == ["Weekly summary"]
    decisions = client.get(f"/projects/{pid}/decisions").json()
    assert [d["title"] for d in decisions] == ["SQLite"]


def test_active_limit_is_enforced_across_the_lifecycle(client):
    # The fixture allows two active projects
    ids = [client.post("/projects", json={"name": n}).json()["id"] for n in ("A", "B", "C")]
    activate = {"status": "active", "next_action": "go"}

    assert client.patch(f"/projects/{ids[0]}", json=activate).status_code == 200
    assert client.patch(f"/projects/{ids[1]}", json=activate).status_code == 200
    assert client.patch(f"/projects/{ids[2]}", json=activate).status_code == 409

    # An already-active project does not compete with itself
    assert client.patch(f"/projects/{ids[0]}", json=activate).status_code == 200

    # Freeing a slot lets the third one in
    client.patch(f"/projects/{ids[1]}", json={"status": "paused"})
    assert client.patch(f"/projects/{ids[2]}", json=activate).status_code == 200
