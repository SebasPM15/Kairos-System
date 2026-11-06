from datetime import UTC, datetime, timedelta

import pytest

from app.models import Project


def make_project(client, name="Rust", status=None, idle_days=0, session=None):
    project = client.post("/projects", json={"name": name}).json()
    if status:
        client.patch(f"/projects/{project['id']}", json={"status": status, "next_action": "go"})
    if idle_days:
        row = session.get(Project, project["id"])
        row.last_activity_at = datetime.now(UTC) - timedelta(days=idle_days)
        session.commit()
    return project


def test_reminders_are_empty_for_a_new_user(client):
    assert client.get("/reminders").json() == {"alerts": [], "suppressed": []}


def test_a_stalled_active_project_appears_with_its_shape(client, session):
    project = make_project(client, status="active", idle_days=12, session=session)

    body = client.get("/reminders").json()

    assert body["suppressed"] == []
    alert = body["alerts"][0]
    assert alert["project_id"] == project["id"]
    assert alert["slug"] == "rust"
    assert alert["kind"] == "stalled"
    assert alert["status"] == "active"
    assert alert["days_idle"] == 12
    assert alert["threshold_days"] == 7
    assert alert["next_action"] == "go"
    assert alert["milestones_total"] == 0
    assert set(alert) == {
        "project_id", "slug", "name", "status", "kind", "days_idle", "threshold_days",
        "next_action", "milestones_total", "last_activity_at",
    }


def test_idle_ideas_and_fresh_projects_do_not_alert(client, session):
    make_project(client, "Idea only", idle_days=90, session=session)
    make_project(client, "Fresh", status="active")

    assert client.get("/reminders").json()["alerts"] == []


def test_snooze_moves_the_project_to_the_suppressed_list_and_reactivating_brings_it_back(client, session):
    project = make_project(client, status="paused", idle_days=40, session=session)

    snoozed = client.patch(f"/projects/{project['id']}/reminders", json={"snooze_days": 7})

    assert snoozed.status_code == 200
    assert snoozed.json()["muted"] is False
    assert snoozed.json()["snoozed_until"]
    body = client.get("/reminders").json()
    assert body["alerts"] == []
    assert [(s["project_id"], s["muted"], s["kind"]) for s in body["suppressed"]] == [(project["id"], False, "stalled")]
    assert body["suppressed"][0]["snoozed_until"] == snoozed.json()["snoozed_until"]

    client.patch(f"/projects/{project['id']}/reminders", json={"snooze_days": None, "muted": False})
    body = client.get("/reminders").json()
    assert [a["project_id"] for a in body["alerts"]] == [project["id"]]
    assert body["suppressed"] == []


def test_mute_is_persistent(client, session):
    project = make_project(client, status="active", idle_days=12, session=session)

    response = client.patch(f"/projects/{project['id']}/reminders", json={"muted": True})

    assert response.json() == {"project_id": project["id"], "snoozed_until": None, "muted": True}
    suppressed = client.get("/reminders").json()["suppressed"]
    assert [(s["muted"], s["snoozed_until"]) for s in suppressed] == [(True, None)]


@pytest.mark.parametrize("body", [{"snooze_days": 0}, {"snooze_days": 31}, {"snooze_days": "x"}, {"muted": "maybe"}])
def test_invalid_bodies_are_422(client, body):
    project = client.post("/projects", json={"name": "A"}).json()

    assert client.patch(f"/projects/{project['id']}/reminders", json=body).status_code == 422


def test_unknown_project_is_404(client):
    assert client.patch("/projects/999/reminders", json={"muted": True}).status_code == 404


def test_another_users_project_is_404_and_untouched(client, users, session):
    project = make_project(client, status="active", idle_days=12, session=session)
    client.as_user(users[1])

    assert client.patch(f"/projects/{project['id']}/reminders", json={"muted": True}).status_code == 404
    assert client.get("/reminders").json() == {"alerts": [], "suppressed": []}

    client.as_user(users[0])
    body = client.get("/reminders").json()
    assert [a["project_id"] for a in body["alerts"]] == [project["id"]]
    assert body["suppressed"] == []
