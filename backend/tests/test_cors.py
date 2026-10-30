from fastapi.testclient import TestClient

from app import main
from app.config import Settings

ALLOWED = "http://localhost:3000"


def _client(monkeypatch, origins: list[str]) -> TestClient:
    monkeypatch.setattr(main, "get_settings", lambda: Settings(cors_origins=origins))
    return TestClient(main.create_app())


def _preflight(client: TestClient, origin: str):
    return client.options(
        "/projects",
        headers={"Origin": origin, "Access-Control-Request-Method": "PATCH"},
    )


def test_preflight_allows_configured_origin(monkeypatch) -> None:
    response = _preflight(_client(monkeypatch, [ALLOWED]), ALLOWED)

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == ALLOWED


def test_preflight_rejects_unlisted_origin(monkeypatch) -> None:
    response = _preflight(_client(monkeypatch, [ALLOWED]), "http://evil.example")

    assert "access-control-allow-origin" not in response.headers


def test_origins_come_from_settings(monkeypatch) -> None:
    other = "http://127.0.0.1:3000"
    response = _preflight(_client(monkeypatch, [other]), other)

    assert response.headers["access-control-allow-origin"] == other
