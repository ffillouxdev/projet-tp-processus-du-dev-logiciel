from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient

from main import app, check_dependencies

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_dependency_overrides() -> Generator[None]:
    yield
    app.dependency_overrides.clear()


def test_health_returns_ok_status() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_health_does_not_require_authentication() -> None:
    # Aucune en-tête d'authentification n'est envoyée.
    response = client.get("/health")
    assert response.status_code == 200


def test_health_reports_available_dependency() -> None:
    app.dependency_overrides[check_dependencies] = lambda: {"database": True}
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["dependencies"] == {"database": "ok"}


def test_health_reports_unavailable_critical_dependency() -> None:
    app.dependency_overrides[check_dependencies] = lambda: {"database": False}
    response = client.get("/health")
    assert response.status_code == 503
    body = response.json()
    assert body["status"] == "unhealthy"
    assert body["dependencies"] == {"database": "unavailable"}
