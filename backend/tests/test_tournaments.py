from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Association, Tournament, User
from app.security import create_access_token
from app.seed import DEMO_PASSWORD, load_demo_data


def _login_headers(client: TestClient, username: str) -> dict[str, str]:
    response = client.post(
        "/auth/login",
        json={"identifier": username, "password": DEMO_PASSWORD},
    )
    assert response.status_code == 200, response.text
    token = str(response.json()["tokens"]["access_token"])
    return {"Authorization": f"Bearer {token}"}


def _user_by_username(db: Session, username: str) -> User:
    return db.scalars(select(User).where(User.username == username)).one()


def _association_by_name(db: Session, name: str) -> Association:
    return db.scalars(select(Association).where(Association.name == name)).one()


def _tournament_by_name(db: Session, name: str) -> Tournament:
    return db.scalars(select(Tournament).where(Tournament.name == name)).one()


# ---------------------------------------------------------------------------
# List visibility filtering (GET /tournaments & GET /associations/{id}/tournaments)
# ---------------------------------------------------------------------------


def test_anonymous_and_unaffiliated_users_only_see_published_tournaments(
    client: TestClient,
    db_session: Session,
) -> None:
    load_demo_data(db_session)
    chess_club = _association_by_name(db_session, "Avignon Chess Club")

    expected_published = {
        "Blitz d'automne",
        "Open rapide d'Avignon",
        "Coupe Rocket League 2v2",
        "Ligue Smash Bros",
    }

    # 1. Anonymous user sees only published tournaments (no draft)
    anon_res = client.get("/tournaments")
    assert anon_res.status_code == 200
    assert {t["name"] for t in anon_res.json()} == expected_published
    assert all(t["status"] != "draft" for t in anon_res.json())

    # Attempting to explicitly filter by status=draft returns empty list
    anon_draft_res = client.get("/tournaments", params={"status": "draft"})
    assert anon_draft_res.status_code == 200
    assert anon_draft_res.json() == []

    # Association tournament listing also hides drafts from anonymous users
    assoc_res = client.get(f"/associations/{chess_club.id}/tournaments")
    assert assoc_res.status_code == 200
    assert {t["name"] for t in assoc_res.json()} == {
        "Blitz d'automne",
        "Open rapide d'Avignon",
    }

    # 2. Newly registered user (belongs to no association) sees only published tournaments
    reg_res = client.post(
        "/auth/register",
        json={
            "email": "outsider@example.com",
            "username": "outsider",
            "password": "Password123!",
            "full_name": "Outsider User",
        },
    )
    assert reg_res.status_code == 201
    outsider_headers = {"Authorization": f"Bearer {reg_res.json()['tokens']['access_token']}"}

    outsider_list = client.get("/tournaments", headers=outsider_headers)
    assert outsider_list.status_code == 200
    assert {t["name"] for t in outsider_list.json()} == expected_published
    assert (
        client.get("/tournaments", headers=outsider_headers, params={"status": "draft"}).json()
        == []
    )


def test_association_members_and_organizers_only_see_own_association_drafts(
    client: TestClient,
    db_session: Session,
) -> None:
    load_demo_data(db_session)
    chess_club = _association_by_name(db_session, "Avignon Chess Club")
    esport_club = _association_by_name(db_session, "Vaucluse eSport")

    # Alice (organizer of Avignon Chess Club) & Chloe (member of Avignon Chess Club)
    for username in ("alice", "chloe"):
        headers = _login_headers(client, username)
        res = client.get("/tournaments", headers=headers)
        assert res.status_code == 200
        names = {t["name"] for t in res.json()}
        assert "Championnat interne" in names
        assert "LAN de printemps" not in names

        drafts = client.get("/tournaments", headers=headers, params={"status": "draft"})
        assert drafts.status_code == 200
        assert [t["name"] for t in drafts.json()] == ["Championnat interne"]

        # Filtering by Vaucluse eSport hides its draft tournament from Chess Club members
        esport_tournaments = client.get(
            f"/associations/{esport_club.id}/tournaments",
            headers=headers,
        )
        assert esport_tournaments.status_code == 200
        assert {t["name"] for t in esport_tournaments.json()} == {
            "Coupe Rocket League 2v2",
            "Ligue Smash Bros",
        }

    # Bob (organizer of Vaucluse eSport) & David (member of Vaucluse eSport)
    for username in ("bob", "david"):
        headers = _login_headers(client, username)
        res = client.get("/tournaments", headers=headers)
        assert res.status_code == 200
        names = {t["name"] for t in res.json()}
        assert "LAN de printemps" in names
        assert "Championnat interne" not in names

        drafts = client.get("/tournaments", headers=headers, params={"status": "draft"})
        assert drafts.status_code == 200
        assert [t["name"] for t in drafts.json()] == ["LAN de printemps"]

        # Filtering by Avignon Chess Club via query parameter hides its draft
        chess_tournaments = client.get(
            "/tournaments",
            headers=headers,
            params={"association_id": chess_club.id},
        )
        assert chess_tournaments.status_code == 200
        assert {t["name"] for t in chess_tournaments.json()} == {
            "Blitz d'automne",
            "Open rapide d'Avignon",
        }


def test_platform_administrator_sees_all_tournaments_including_all_drafts(
    client: TestClient,
    db_session: Session,
) -> None:
    load_demo_data(db_session)
    admin_headers = _login_headers(client, "admin")

    all_res = client.get("/tournaments", headers=admin_headers)
    assert all_res.status_code == 200
    assert {t["name"] for t in all_res.json()} == {
        "Blitz d'automne",
        "Open rapide d'Avignon",
        "Championnat interne",
        "Coupe Rocket League 2v2",
        "Ligue Smash Bros",
        "LAN de printemps",
    }

    drafts_res = client.get("/tournaments", headers=admin_headers, params={"status": "draft"})
    assert drafts_res.status_code == 200
    assert {t["name"] for t in drafts_res.json()} == {
        "Championnat interne",
        "LAN de printemps",
    }


# ---------------------------------------------------------------------------
# Direct access by ID (GET /tournaments/{tournament_id})
# ---------------------------------------------------------------------------


def test_direct_access_by_id_enforces_access_control(
    client: TestClient,
    db_session: Session,
) -> None:
    load_demo_data(db_session)

    published_chess = _tournament_by_name(db_session, "Open rapide d'Avignon")
    draft_chess = _tournament_by_name(db_session, "Championnat interne")
    draft_esport = _tournament_by_name(db_session, "LAN de printemps")

    admin_headers = _login_headers(client, "admin")
    alice_headers = _login_headers(client, "alice")
    chloe_headers = _login_headers(client, "chloe")
    bob_headers = _login_headers(client, "bob")
    david_headers = _login_headers(client, "david")

    # 1. Published tournament is accessible by ID to everyone (anonymous & authenticated)
    for headers in (None, alice_headers, chloe_headers, bob_headers, david_headers, admin_headers):
        res = client.get(f"/tournaments/{published_chess.id}", headers=headers)
        assert res.status_code == 200
        assert res.json()["name"] == "Open rapide d'Avignon"
        assert res.json()["association"]["name"] == "Avignon Chess Club"
        assert {p["user"]["username"] for p in res.json()["participants"]} == {"chloe", "emma"}

    # 2. Protected tournament (Avignon Chess Club draft):
    # Allowed: admin, alice (organizer), chloe (member)
    for headers in (admin_headers, alice_headers, chloe_headers):
        res = client.get(f"/tournaments/{draft_chess.id}", headers=headers)
        assert res.status_code == 200
        assert res.json()["name"] == "Championnat interne"
        assert res.json()["status"] == "draft"

    # Refused (403 Forbidden): anonymous, bob (other club organizer), david (other club member)
    for headers in (None, bob_headers, david_headers):
        res = client.get(f"/tournaments/{draft_chess.id}", headers=headers)
        assert res.status_code == 403

    # 3. Protected tournament (Vaucluse eSport draft):
    # Allowed: admin, bob (organizer), david (member)
    for headers in (admin_headers, bob_headers, david_headers):
        res = client.get(f"/tournaments/{draft_esport.id}", headers=headers)
        assert res.status_code == 200
        assert res.json()["name"] == "LAN de printemps"

    # Refused (403 Forbidden): anonymous, alice, chloe
    for headers in (None, alice_headers, chloe_headers):
        res = client.get(f"/tournaments/{draft_esport.id}", headers=headers)
        assert res.status_code == 403

    # 4. Non-existent tournament ID returns 404 Not Found
    assert client.get("/tournaments/999999").status_code == 404
    assert client.get("/tournaments/999999", headers=admin_headers).status_code == 404
    assert client.get("/associations/999999/tournaments").status_code == 404


def test_invalid_token_and_inactive_user_are_rejected_on_tournament_endpoints(
    client: TestClient,
    db_session: Session,
) -> None:
    load_demo_data(db_session)
    published = _tournament_by_name(db_session, "Open rapide d'Avignon")
    hugo = _user_by_username(db_session, "hugo")

    invalid_headers = {"Authorization": "Bearer invalid.jwt.token"}
    hugo_headers = {"Authorization": f"Bearer {create_access_token(user_id=hugo.id)}"}

    # Invalid token -> 401 Unauthorized
    assert client.get("/tournaments", headers=invalid_headers).status_code == 401
    assert client.get(f"/tournaments/{published.id}", headers=invalid_headers).status_code == 401

    # Inactive user -> 403 Forbidden
    assert client.get("/tournaments", headers=hugo_headers).status_code == 403
    assert client.get(f"/tournaments/{published.id}", headers=hugo_headers).status_code == 403


# ---------------------------------------------------------------------------
# Tournament CRUD & Write Authorization (POST, PATCH, DELETE /tournaments)
# ---------------------------------------------------------------------------


def test_organizer_and_admin_can_create_publish_update_and_delete_tournament(
    client: TestClient,
    db_session: Session,
) -> None:
    load_demo_data(db_session)
    chess_club = _association_by_name(db_session, "Avignon Chess Club")

    alice_headers = _login_headers(client, "alice")
    david_headers = _login_headers(client, "david")
    admin_headers = _login_headers(client, "admin")

    start = datetime.now(UTC) + timedelta(days=10)
    end = start + timedelta(days=2)

    # 1. Alice (organizer of Avignon Chess Club) creates a draft tournament
    create_res = client.post(
        "/tournaments",
        headers=alice_headers,
        json={
            "name": "Tournoi de Noël",
            "description": "Tournoi interne en préparation",
            "status": "draft",
            "max_participants": 24,
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
            "association_id": chess_club.id,
        },
    )
    assert create_res.status_code == 201
    tournament_id = int(create_res.json()["id"])
    assert create_res.json()["status"] == "draft"

    # While in draft: David (non-member of Chess Club) cannot see it, Admin and Alice can
    assert client.get(f"/tournaments/{tournament_id}", headers=david_headers).status_code == 403
    assert client.get(f"/tournaments/{tournament_id}", headers=alice_headers).status_code == 200
    assert client.get(f"/tournaments/{tournament_id}", headers=admin_headers).status_code == 200

    # 2. Alice publishes the tournament (status -> "open")
    patch_res = client.patch(
        f"/tournaments/{tournament_id}",
        headers=alice_headers,
        json={"status": "open", "description": "Inscriptions ouvertes à tous !"},
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["status"] == "open"

    # Now David and anonymous users can see it both in list and by ID
    assert client.get(f"/tournaments/{tournament_id}", headers=david_headers).status_code == 200
    assert client.get(f"/tournaments/{tournament_id}").status_code == 200

    # 3. Platform admin can also update and delete any tournament
    admin_patch = client.patch(
        f"/tournaments/{tournament_id}",
        headers=admin_headers,
        json={"name": "Grand Tournoi de Noël", "max_participants": 32},
    )
    assert admin_patch.status_code == 200
    assert admin_patch.json()["name"] == "Grand Tournoi de Noël"
    assert admin_patch.json()["max_participants"] == 32

    del_res = client.delete(f"/tournaments/{tournament_id}", headers=admin_headers)
    assert del_res.status_code == 204
    assert client.get(f"/tournaments/{tournament_id}", headers=admin_headers).status_code == 404


def test_unauthorized_users_cannot_create_update_or_delete_tournaments(
    client: TestClient,
    db_session: Session,
) -> None:
    load_demo_data(db_session)
    chess_club = _association_by_name(db_session, "Avignon Chess Club")
    draft_chess = _tournament_by_name(db_session, "Championnat interne")

    chloe_headers = _login_headers(client, "chloe")  # simple member of Avignon Chess Club
    bob_headers = _login_headers(client, "bob")  # organizer of Vaucluse eSport (other club)
    david_headers = _login_headers(client, "david")  # member of Vaucluse eSport
    admin_headers = _login_headers(client, "admin")

    payload = {
        "name": "Tournoi Pirate",
        "association_id": chess_club.id,
    }

    # Unauthenticated requests -> 401
    assert client.post("/tournaments", json=payload).status_code == 401
    assert (
        client.patch(f"/tournaments/{draft_chess.id}", json={"status": "open"}).status_code == 401
    )
    assert client.delete(f"/tournaments/{draft_chess.id}").status_code == 401

    # Authenticated without organizer/admin rights in Avignon Chess Club -> 403
    for headers in (chloe_headers, bob_headers, david_headers):
        assert client.post("/tournaments", headers=headers, json=payload).status_code == 403
        assert (
            client.patch(
                f"/tournaments/{draft_chess.id}",
                headers=headers,
                json={"status": "open"},
            ).status_code
            == 403
        )
        assert client.delete(f"/tournaments/{draft_chess.id}", headers=headers).status_code == 403

    # Validation & 404 checks for admin/organizer
    assert (
        client.post(
            "/tournaments",
            headers=admin_headers,
            json={"name": "Tournoi Orphelin", "association_id": 999999},
        ).status_code
        == 404
    )
    assert (
        client.patch(
            "/tournaments/999999",
            headers=admin_headers,
            json={"name": "Inexistant"},
        ).status_code
        == 404
    )
    assert client.delete("/tournaments/999999", headers=admin_headers).status_code == 404

    # Invalid date range (end_date < start_date) returns 422
    now = datetime.now(UTC)
    assert (
        client.post(
            "/tournaments",
            headers=admin_headers,
            json={
                "name": "Dates invalides",
                "association_id": chess_club.id,
                "start_date": (now + timedelta(days=5)).isoformat(),
                "end_date": (now + timedelta(days=2)).isoformat(),
            },
        ).status_code
        == 422
    )
    assert (
        client.patch(
            f"/tournaments/{draft_chess.id}",
            headers=admin_headers,
            json={
                "start_date": (now + timedelta(days=10)).isoformat(),
                "end_date": (now + timedelta(days=1)).isoformat(),
            },
        ).status_code
        == 422
    )


# ---------------------------------------------------------------------------
# Joining a tournament (POST /tournaments/{id}/participants)
# ---------------------------------------------------------------------------


def _participant_usernames(client: TestClient, tournament_id: int) -> set[str]:
    response = client.get(f"/tournaments/{tournament_id}")
    assert response.status_code == 200, response.text
    return {p["user"]["username"] for p in response.json()["participants"]}


def test_authenticated_player_can_join_open_tournament(
    client: TestClient,
    db_session: Session,
) -> None:
    load_demo_data(db_session)
    smash = _tournament_by_name(db_session, "Ligue Smash Bros")
    alice = _user_by_username(db_session, "alice")

    res = client.post(
        f"/tournaments/{smash.id}/participants", headers=_login_headers(client, "alice")
    )

    assert res.status_code == 201, res.text
    body = res.json()
    assert body["tournament_id"] == smash.id
    assert body["user_id"] == alice.id
    assert body["user"]["username"] == "alice"
    assert body["registered_at"]
    assert _participant_usernames(client, smash.id) == {"emma", "alice"}


def test_anonymous_and_inactive_users_cannot_join(
    client: TestClient,
    db_session: Session,
) -> None:
    load_demo_data(db_session)
    smash = _tournament_by_name(db_session, "Ligue Smash Bros")

    assert client.post(f"/tournaments/{smash.id}/participants").status_code == 401

    hugo = _user_by_username(db_session, "hugo")
    hugo_headers = {"Authorization": f"Bearer {create_access_token(user_id=hugo.id)}"}
    res = client.post(f"/tournaments/{smash.id}/participants", headers=hugo_headers)
    assert res.status_code == 403

    assert _participant_usernames(client, smash.id) == {"emma"}


def test_cannot_join_twice(client: TestClient, db_session: Session) -> None:
    load_demo_data(db_session)
    smash = _tournament_by_name(db_session, "Ligue Smash Bros")

    res = client.post(
        f"/tournaments/{smash.id}/participants", headers=_login_headers(client, "emma")
    )

    assert res.status_code == 409
    assert res.json()["detail"] == "Already registered in this tournament"
    assert _participant_usernames(client, smash.id) == {"emma"}


def test_cannot_join_tournament_that_is_not_open(
    client: TestClient,
    db_session: Session,
) -> None:
    load_demo_data(db_session)
    alice_headers = _login_headers(client, "alice")

    # ongoing, finished, and a draft the user is allowed to see (alice organizes the club)
    for name in ("Open rapide d'Avignon", "Blitz d'automne", "Championnat interne"):
        tournament = _tournament_by_name(db_session, name)
        res = client.post(f"/tournaments/{tournament.id}/participants", headers=alice_headers)
        assert res.status_code == 409, name
        assert res.json()["detail"] == "Tournament registrations are not open"


def test_cannot_join_hidden_draft_or_missing_tournament(
    client: TestClient,
    db_session: Session,
) -> None:
    load_demo_data(db_session)
    draft_esport = _tournament_by_name(db_session, "LAN de printemps")
    alice_headers = _login_headers(client, "alice")

    res = client.post(f"/tournaments/{draft_esport.id}/participants", headers=alice_headers)
    assert res.status_code == 403

    res = client.post("/tournaments/999999/participants", headers=alice_headers)
    assert res.status_code == 404


def test_cannot_join_full_tournament(client: TestClient, db_session: Session) -> None:
    load_demo_data(db_session)
    rocket = _tournament_by_name(db_session, "Coupe Rocket League 2v2")
    rocket.max_participants = 3  # david and chloe are already registered
    db_session.commit()

    res = client.post(
        f"/tournaments/{rocket.id}/participants", headers=_login_headers(client, "alice")
    )
    assert res.status_code == 201, res.text

    res = client.post(
        f"/tournaments/{rocket.id}/participants", headers=_login_headers(client, "emma")
    )
    assert res.status_code == 409
    assert res.json()["detail"] == "Tournament is full"
    assert _participant_usernames(client, rocket.id) == {"david", "chloe", "alice"}


# ---------------------------------------------------------------------------
# Leaving a tournament (DELETE /tournaments/{id}/participants/me)
# ---------------------------------------------------------------------------


def test_registered_player_can_leave_open_tournament(
    client: TestClient,
    db_session: Session,
) -> None:
    load_demo_data(db_session)
    rocket = _tournament_by_name(db_session, "Coupe Rocket League 2v2")
    david_headers = _login_headers(client, "david")

    res = client.delete(f"/tournaments/{rocket.id}/participants/me", headers=david_headers)
    assert res.status_code == 204
    assert _participant_usernames(client, rocket.id) == {"chloe"}

    # Leaving again: not registered anymore
    res = client.delete(f"/tournaments/{rocket.id}/participants/me", headers=david_headers)
    assert res.status_code == 404
    assert res.json()["detail"] == "Not registered in this tournament"

    # The freed seat can be taken again
    res = client.post(f"/tournaments/{rocket.id}/participants", headers=david_headers)
    assert res.status_code == 201


def test_cannot_leave_without_auth_or_once_registrations_are_closed(
    client: TestClient,
    db_session: Session,
) -> None:
    load_demo_data(db_session)
    smash = _tournament_by_name(db_session, "Ligue Smash Bros")
    ongoing = _tournament_by_name(db_session, "Open rapide d'Avignon")
    finished = _tournament_by_name(db_session, "Blitz d'automne")
    emma_headers = _login_headers(client, "emma")

    assert client.delete(f"/tournaments/{smash.id}/participants/me").status_code == 401

    for tournament in (ongoing, finished):  # emma is registered in both
        res = client.delete(f"/tournaments/{tournament.id}/participants/me", headers=emma_headers)
        assert res.status_code == 409
        assert res.json()["detail"] == "Tournament registrations are not open"
    assert "emma" in _participant_usernames(client, ongoing.id)

    res = client.delete("/tournaments/999999/participants/me", headers=emma_headers)
    assert res.status_code == 404
