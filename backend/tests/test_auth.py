from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import User


def test_register_success(client: TestClient):
    response = client.post(
        "/auth/register",
        json={
            "email": "user@example.com",
            "username": "gamer123",
            "password": "Password123!",
            "full_name": "Pro Gamer",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert "user" in data
    assert "tokens" in data
    assert data["user"]["email"] == "user@example.com"
    assert data["user"]["username"] == "gamer123"
    assert data["user"]["full_name"] == "Pro Gamer"
    assert data["user"]["is_active"] is True
    assert "hashed_password" not in data["user"]
    assert "access_token" in data["tokens"]
    assert "refresh_token" in data["tokens"]
    assert data["tokens"]["token_type"] == "bearer"


def test_register_assigns_default_participant_role(client: TestClient, db_session: Session):
    response = client.post(
        "/auth/register",
        json={"email": "role@example.com", "username": "roleuser", "password": "Password123!"},
    )
    assert response.status_code == 201
    user = db_session.scalar(select(User).where(User.username == "roleuser"))
    assert user is not None
    assert user.role.name == "participant"


def test_register_duplicate_email(client: TestClient):
    payload = {
        "email": "duplicate@example.com",
        "username": "userone",
        "password": "Password123!",
    }
    first_res = client.post("/auth/register", json=payload)
    assert first_res.status_code == 201

    payload2 = {
        "email": "duplicate@example.com",
        "username": "usertwo",
        "password": "Password123!",
    }
    second_res = client.post("/auth/register", json=payload2)
    assert second_res.status_code == 409
    assert "email already exists" in second_res.json()["detail"].lower()


def test_register_duplicate_username(client: TestClient):
    payload = {
        "email": "user1@example.com",
        "username": "samenick",
        "password": "Password123!",
    }
    first_res = client.post("/auth/register", json=payload)
    assert first_res.status_code == 201

    payload2 = {
        "email": "user2@example.com",
        "username": "samenick",
        "password": "Password123!",
    }
    second_res = client.post("/auth/register", json=payload2)
    assert second_res.status_code == 409
    assert "username already exists" in second_res.json()["detail"].lower()


def test_register_password_validation(client: TestClient):
    # Too short
    res_short = client.post(
        "/auth/register",
        json={"email": "val@example.com", "username": "validname", "password": "123"},
    )
    assert res_short.status_code == 422

    # No numbers
    res_no_num = client.post(
        "/auth/register",
        json={"email": "val2@example.com", "username": "validname2", "password": "onlylettershere"},
    )
    assert res_no_num.status_code == 422

    # No letters
    res_no_alpha = client.post(
        "/auth/register",
        json={"email": "val3@example.com", "username": "validname3", "password": "1234567890"},
    )
    assert res_no_alpha.status_code == 422


def test_register_invalid_username_format(client: TestClient):
    res = client.post(
        "/auth/register",
        json={"email": "val@example.com", "username": "bad user name!", "password": "Password123!"},
    )
    assert res.status_code == 422


def test_login_with_email_success(client: TestClient):
    client.post(
        "/auth/register",
        json={"email": "login@example.com", "username": "loginuser", "password": "Password123!"},
    )

    response = client.post(
        "/auth/login",
        json={"identifier": "login@example.com", "password": "Password123!"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["user"]["email"] == "login@example.com"
    assert "access_token" in data["tokens"]
    assert "refresh_token" in data["tokens"]


def test_login_with_username_success(client: TestClient):
    client.post(
        "/auth/register",
        json={"email": "login2@example.com", "username": "player99", "password": "Password123!"},
    )

    response = client.post(
        "/auth/login",
        json={"identifier": "player99", "password": "Password123!"},
    )
    assert response.status_code == 200
    assert response.json()["user"]["username"] == "player99"


def test_login_invalid_password(client: TestClient):
    client.post(
        "/auth/register",
        json={"email": "login3@example.com", "username": "player100", "password": "Password123!"},
    )

    response = client.post(
        "/auth/login",
        json={"identifier": "player100", "password": "WrongPassword123!"},
    )
    assert response.status_code == 401
    assert "incorrect" in response.json()["detail"].lower()


def test_login_nonexistent_user(client: TestClient):
    response = client.post(
        "/auth/login",
        json={"identifier": "nonexistent@example.com", "password": "Password123!"},
    )
    assert response.status_code == 401


def test_login_oauth2_form_token(client: TestClient):
    client.post(
        "/auth/register",
        json={"email": "oauth@example.com", "username": "oauthuser", "password": "Password123!"},
    )

    response = client.post(
        "/auth/token",
        data={"username": "oauthuser", "password": "Password123!"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


def test_get_current_user_profile(client: TestClient):
    reg = client.post(
        "/auth/register",
        json={"email": "me@example.com", "username": "meuser", "password": "Password123!"},
    )
    token = reg.json()["tokens"]["access_token"]

    response = client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert response.json()["email"] == "me@example.com"
    assert response.json()["username"] == "meuser"


def test_get_current_user_unauthorized(client: TestClient):
    # No auth header
    res_no_auth = client.get("/auth/me")
    assert res_no_auth.status_code == 401

    # Invalid token string
    res_bad_token = client.get("/auth/me", headers={"Authorization": "Bearer invalidtokenstr"})
    assert res_bad_token.status_code == 401


def test_get_current_user_rejects_refresh_token(client: TestClient):
    reg = client.post(
        "/auth/register",
        json={"email": "rf@example.com", "username": "rfuser", "password": "Password123!"},
    )
    refresh_token = reg.json()["tokens"]["refresh_token"]

    response = client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {refresh_token}"},
    )
    assert response.status_code == 401
    assert "access token required" in response.json()["detail"].lower()


def test_patch_profile(client: TestClient):
    reg = client.post(
        "/auth/register",
        json={"email": "patch@example.com", "username": "patchuser", "password": "Password123!"},
    )
    token = reg.json()["tokens"]["access_token"]

    update_res = client.patch(
        "/auth/me",
        headers={"Authorization": f"Bearer {token}"},
        json={"full_name": "Updated Name", "username": "newusername"},
    )
    assert update_res.status_code == 200
    data = update_res.json()
    assert data["full_name"] == "Updated Name"
    assert data["username"] == "newusername"


def test_change_password_flow(client: TestClient):
    reg = client.post(
        "/auth/register",
        json={
            "email": "chpass@example.com",
            "username": "chpassuser",
            "password": "OldPassword123!",
        },
    )
    token = reg.json()["tokens"]["access_token"]

    # Attempt with wrong current password
    fail_res = client.post(
        "/auth/change-password",
        headers={"Authorization": f"Bearer {token}"},
        json={"current_password": "WrongOldPassword123!", "new_password": "NewPassword123!"},
    )
    assert fail_res.status_code == 400

    # Successful change
    ok_res = client.post(
        "/auth/change-password",
        headers={"Authorization": f"Bearer {token}"},
        json={"current_password": "OldPassword123!", "new_password": "NewPassword123!"},
    )
    assert ok_res.status_code == 200

    # Old password no longer works
    login_old = client.post(
        "/auth/login",
        json={"identifier": "chpassuser", "password": "OldPassword123!"},
    )
    assert login_old.status_code == 401

    # New password works
    login_new = client.post(
        "/auth/login",
        json={"identifier": "chpassuser", "password": "NewPassword123!"},
    )
    assert login_new.status_code == 200
