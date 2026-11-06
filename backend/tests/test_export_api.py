import pytest

from app.config import Settings, get_settings


@pytest.fixture
def vault(tmp_path, client):
    root = tmp_path / "vault"
    root.mkdir()
    client.app.dependency_overrides[get_settings] = lambda: Settings(
        obsidian_vault_path=str(root), max_active_projects=2
    )
    return root


def test_export_returns_the_summary_and_writes_the_vault(client, vault):
    client.post("/projects", json={"name": "Kairos"})
    client.post("/ideas", json={"content": "suelta"})

    response = client.post("/export")

    assert response.status_code == 200
    assert response.json() == {
        "projects_exported": 1,
        "files_written": 5,
        "files_unchanged": 0,
        "orphans": [],
    }
    assert (vault / "Kairos" / "kairos" / "README.md").is_file()
    assert "suelta" in (vault / "Kairos" / "_bandeja.md").read_text(encoding="utf-8")


def test_second_export_reports_everything_unchanged(client, vault):
    client.post("/projects", json={"name": "Kairos"})
    client.post("/export")

    body = client.post("/export").json()

    assert (body["files_written"], body["files_unchanged"]) == (0, 5)


def test_export_reports_orphans(client, vault):
    (vault / "Kairos" / "huerfano").mkdir(parents=True)

    assert client.post("/export").json()["orphans"] == ["huerfano"]


def test_export_without_a_configured_vault_is_a_conflict(client):
    response = client.post("/export")

    assert response.status_code == 409
    assert "vault" in response.json()["detail"].lower()


def test_export_with_a_missing_vault_root_is_a_conflict_and_creates_nothing(client, tmp_path):
    missing = tmp_path / "no-existe"
    client.app.dependency_overrides[get_settings] = lambda: Settings(obsidian_vault_path=str(missing))

    assert client.post("/export").status_code == 409
    assert not missing.exists()


def test_export_only_includes_the_current_users_projects(client, users, vault):
    client.post("/projects", json={"name": "Mio"})
    client.as_user(users[1])
    client.post("/projects", json={"name": "Ajeno"})
    client.as_user(users[0])

    body = client.post("/export").json()

    assert body["projects_exported"] == 1
    assert (vault / "Kairos" / "mio").is_dir()
    assert not (vault / "Kairos" / "ajeno").exists()


def test_reminder_state_never_reaches_the_vault(client, vault, session, users):
    from datetime import UTC, date, datetime

    from app.models import ReminderKind, ReminderLog

    project = client.post("/projects", json={"name": "Kairos"}).json()
    session.add(ReminderLog(
        user_id=users[0].id, project_id=project["id"], kind=ReminderKind.STALLED,
        sent_at=datetime.now(UTC), local_date=date.today(),
    ))
    session.commit()
    first = client.post("/export").json()
    before = {p: p.read_text(encoding="utf-8") for p in vault.rglob("*.md")}

    client.patch(f"/projects/{project['id']}/reminders", json={"muted": True, "snooze_days": 5})
    second = client.post("/export").json()

    assert (first["files_written"], second["files_written"], second["files_unchanged"]) == (5, 0, 5)
    assert {p.name for p in before} == {"README.md", "hitos.md", "ideas.md", "decisiones.md", "_bandeja.md"}
    for text in before.values():
        for word in ("muted", "snooze", "reminder", "silenci", "recordatorio"):
            assert word not in text.lower()
    assert {p: p.read_text(encoding="utf-8") for p in vault.rglob("*.md")} == before
