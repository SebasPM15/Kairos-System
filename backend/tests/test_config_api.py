def test_config_exposes_active_limit(client) -> None:
    # The shared `client` fixture overrides settings with max_active_projects=2
    response = client.get("/config")

    assert response.status_code == 200
    assert response.json() == {"max_active_projects": 2}
