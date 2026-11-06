from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def test_root_returns_hello_world() -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == "Hello World"
