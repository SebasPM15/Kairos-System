import inspect
from unittest.mock import patch

import pytest

from app.config import Settings, get_settings
from app.exporters.vault import FileSystemVaultWriter
from app.services import errors

# Each domain error mapped to the HTTP status it must produce
EXPECTED_STATUS = {
    errors.ProjectNotFound: 404,
    errors.MilestoneNotFound: 404,
    errors.IdeaNotFound: 404,
    errors.DecisionNotFound: 404,
    errors.ActiveLimitReached: 409,
    errors.NextActionRequired: 422,
    errors.VaultNotConfigured: 409,
    errors.UnsafeVaultPath: 409,
}


def test_every_domain_error_has_an_expected_status():
    declared = {
        cls
        for _, cls in inspect.getmembers(errors, inspect.isclass)
        if issubclass(cls, errors.DomainError) and cls is not errors.DomainError
    }

    assert declared == set(EXPECTED_STATUS)


def trigger_project_not_found(client):
    return client.get("/projects/999")


def trigger_milestone_not_found(client):
    return client.patch("/milestones/999", json={"done": True})


def trigger_idea_not_found(client):
    return client.delete("/ideas/999")


def trigger_decision_not_found(client):
    return client.delete("/decisions/999")


def trigger_active_limit_reached(client):
    # The fixture allows two active projects, so the third is rejected
    for name in ("A", "B", "C"):
        pid = client.post("/projects", json={"name": name}).json()["id"]
        response = client.patch(f"/projects/{pid}", json={"status": "active", "next_action": "go"})
    return response


def trigger_next_action_required(client):
    pid = client.post("/projects", json={"name": "A"}).json()["id"]
    return client.patch(f"/projects/{pid}", json={"status": "active"})


def trigger_vault_not_configured(client):
    # The fixture settings leave OBSIDIAN_VAULT_PATH empty
    return client.post("/export")


def trigger_unsafe_vault_path(client, tmp_path):
    client.app.dependency_overrides[get_settings] = lambda: Settings(obsidian_vault_path=str(tmp_path))
    with patch.object(FileSystemVaultWriter, "write", side_effect=errors.UnsafeVaultPath("x")):
        return client.post("/export")


TRIGGERS = {
    errors.ProjectNotFound: trigger_project_not_found,
    errors.MilestoneNotFound: trigger_milestone_not_found,
    errors.IdeaNotFound: trigger_idea_not_found,
    errors.DecisionNotFound: trigger_decision_not_found,
    errors.ActiveLimitReached: trigger_active_limit_reached,
    errors.NextActionRequired: trigger_next_action_required,
    errors.VaultNotConfigured: trigger_vault_not_configured,
    errors.UnsafeVaultPath: trigger_unsafe_vault_path,
}


@pytest.mark.parametrize("error", EXPECTED_STATUS, ids=lambda e: e.__name__)
def test_domain_error_maps_to_http_status(client, error, tmp_path):
    trigger = TRIGGERS[error]
    takes_path = "tmp_path" in inspect.signature(trigger).parameters
    response = trigger(client, tmp_path) if takes_path else trigger(client)

    assert response.status_code == EXPECTED_STATUS[error]
    assert response.json()["detail"]
