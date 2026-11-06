from datetime import UTC, datetime, timedelta

import jwt
from fastapi.testclient import TestClient

from app.config import settings


def test_token_refresh_success(client: TestClient):
    reg = client.post(
        "/auth/register",
        json={"email": "ref@example.com", "username": "refuser", "password": "Password123!"},
    )
    tokens = reg.json()["tokens"]
    refresh_token = tokens["refresh_token"]

    response = client.post(
        "/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert response.status_code == 200
    new_tokens = response.json()
    assert "access_token" in new_tokens
    assert "refresh_token" in new_tokens
    assert new_tokens["refresh_token"] != refresh_token


def test_token_rotation_and_reuse_detection(client: TestClient):
    reg = client.post(
        "/auth/register",
        json={"email": "replay@example.com", "username": "replayuser", "password": "Password123!"},
    )
    original_refresh_token = reg.json()["tokens"]["refresh_token"]

    # First refresh succeeds
    first_refresh = client.post(
        "/auth/refresh",
        json={"refresh_token": original_refresh_token},
    )
    assert first_refresh.status_code == 200
    second_refresh_token = first_refresh.json()["refresh_token"]

    # Replay attack attempt: reuse the original (already consumed) refresh token
    reuse_attempt = client.post(
        "/auth/refresh",
        json={"refresh_token": original_refresh_token},
    )
    assert reuse_attempt.status_code == 401
    assert "revoked" in reuse_attempt.json()["detail"].lower()

    # As a security measure against replay attacks, the second token should now also be invalidated
    subsequent_attempt = client.post(
        "/auth/refresh",
        json={"refresh_token": second_refresh_token},
    )
    assert subsequent_attempt.status_code == 401


def test_refresh_rejects_access_token(client: TestClient):
    reg = client.post(
        "/auth/register",
        json={"email": "acc@example.com", "username": "accuser", "password": "Password123!"},
    )
    access_token = reg.json()["tokens"]["access_token"]

    response = client.post(
        "/auth/refresh",
        json={"refresh_token": access_token},
    )
    assert response.status_code == 401
    assert "refresh token required" in response.json()["detail"].lower()


def test_refresh_rejects_expired_token(client: TestClient):
    # Manually create an already expired token
    now = datetime.now(UTC)
    expired_payload = {
        "sub": "1",
        "jti": "fakejti123",
        "type": "refresh",
        "iat": int((now - timedelta(days=10)).timestamp()),
        "exp": int((now - timedelta(days=1)).timestamp()),
    }
    expired_token = jwt.encode(expired_payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

    response = client.post(
        "/auth/refresh",
        json={"refresh_token": expired_token},
    )
    assert response.status_code == 401
    assert "expired" in response.json()["detail"].lower()


def test_logout_revokes_refresh_token(client: TestClient):
    reg = client.post(
        "/auth/register",
        json={"email": "logout@example.com", "username": "logoutuser", "password": "Password123!"},
    )
    refresh_token = reg.json()["tokens"]["refresh_token"]

    # Logout with refresh token
    logout_res = client.post(
        "/auth/logout",
        json={"refresh_token": refresh_token},
    )
    assert logout_res.status_code == 200

    # Refresh should now be denied
    refresh_res = client.post(
        "/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert refresh_res.status_code == 401


def test_logout_all_devices(client: TestClient):
    reg = client.post(
        "/auth/register",
        json={
            "email": "logoutall@example.com",
            "username": "logoutalluser",
            "password": "Password123!",
        },
    )
    token1 = reg.json()["tokens"]["access_token"]
    refresh1 = reg.json()["tokens"]["refresh_token"]

    # Login a second time (second session/device)
    login2 = client.post(
        "/auth/login",
        json={"identifier": "logoutalluser", "password": "Password123!"},
    )
    refresh2 = login2.json()["tokens"]["refresh_token"]

    # Logout all devices using access token
    logout_all_res = client.post(
        "/auth/logout-all",
        headers={"Authorization": f"Bearer {token1}"},
    )
    assert logout_all_res.status_code == 200

    # Both refresh tokens should now be rejected
    assert client.post("/auth/refresh", json={"refresh_token": refresh1}).status_code == 401
    assert client.post("/auth/refresh", json={"refresh_token": refresh2}).status_code == 401
