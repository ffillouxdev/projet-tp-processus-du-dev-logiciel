import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import _build_parser, create_admin_user, promote_user_to_admin
from app.models import Association, Membership, Role, User
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


def _role_by_name(db: Session, name: str) -> Role:
    return db.scalars(select(Role).where(Role.name == name)).one()


# ---------------------------------------------------------------------------
# Public consultation of Demo Dataset ("savoir qui organise")
# ---------------------------------------------------------------------------


def test_public_endpoints_expose_demo_associations_roles_and_organizers(
    client: TestClient,
    db_session: Session,
) -> None:
    load_demo_data(db_session)
    chess_club = _association_by_name(db_session, "Avignon Chess Club")
    esport_club = _association_by_name(db_session, "Vaucluse eSport")

    # Public list of roles seeded by demo dataset
    roles_res = client.get("/roles")
    assert roles_res.status_code == 200
    assert {r["name"] for r in roles_res.json()} == {"member", "organizer"}

    # Public list of associations
    assoc_res = client.get("/associations")
    assert assoc_res.status_code == 200
    assert [a["name"] for a in assoc_res.json()] == ["Avignon Chess Club", "Vaucluse eSport"]

    # Detail view exposes memberships with users and roles
    detail_res = client.get(f"/associations/{chess_club.id}")
    assert detail_res.status_code == 200
    members_by_username = {
        m["user"]["username"]: m["role"]["name"] for m in detail_res.json()["memberships"]
    }
    assert members_by_username == {"alice": "organizer", "chloe": "member"}

    # Filter specifically who organizes each association
    chess_orgs = client.get(
        f"/associations/{chess_club.id}/members",
        params={"role": "organizer"},
    )
    assert chess_orgs.status_code == 200
    assert [m["user"]["username"] for m in chess_orgs.json()] == ["alice"]

    esport_orgs = client.get(
        f"/associations/{esport_club.id}/members",
        params={"role": "organizer"},
    )
    assert esport_orgs.status_code == 200
    assert [m["user"]["username"] for m in esport_orgs.json()] == ["bob"]


# ---------------------------------------------------------------------------
# Roles CRUD & Authorization (using demo `admin`)
# ---------------------------------------------------------------------------


def test_demo_admin_can_create_update_and_delete_role(
    client: TestClient,
    db_session: Session,
) -> None:
    load_demo_data(db_session)
    admin_headers = _login_headers(client, "admin")

    # Create a new role
    create_res = client.post(
        "/roles",
        headers=admin_headers,
        json={"name": "referee", "description": "Arbitre les rencontres"},
    )
    assert create_res.status_code == 201
    role_id = int(create_res.json()["id"])
    assert create_res.json()["name"] == "referee"

    # Duplicate role name returns 409 Conflict
    dup_res = client.post("/roles", headers=admin_headers, json={"name": "organizer"})
    assert dup_res.status_code == 409

    # Get & Update role
    assert client.get(f"/roles/{role_id}").status_code == 200
    patch_res = client.patch(
        f"/roles/{role_id}",
        headers=admin_headers,
        json={"description": "Arbitre officiel des tournois"},
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["description"] == "Arbitre officiel des tournois"

    # Unused role can be deleted
    del_res = client.delete(f"/roles/{role_id}", headers=admin_headers)
    assert del_res.status_code == 204
    assert client.get(f"/roles/{role_id}").status_code == 404

    # Deleting a role currently assigned in demo memberships (`organizer`) returns 409
    organizer_role = _role_by_name(db_session, "organizer")
    in_use_del = client.delete(f"/roles/{organizer_role.id}", headers=admin_headers)
    assert in_use_del.status_code == 409
    assert "assigned" in in_use_del.json()["detail"].lower()


# ---------------------------------------------------------------------------
# Associations, Memberships & Role Assignment
# ---------------------------------------------------------------------------


def test_demo_admin_creates_association_and_assigns_roles(
    client: TestClient,
    db_session: Session,
) -> None:
    load_demo_data(db_session)
    admin_headers = _login_headers(client, "admin")
    david_headers = _login_headers(client, "david")

    organizer_role = _role_by_name(db_session, "organizer")
    member_role = _role_by_name(db_session, "member")
    david = _user_by_username(db_session, "david")
    emma = _user_by_username(db_session, "emma")

    # 1. Admin creates a new association
    create_assoc = client.post(
        "/associations",
        headers=admin_headers,
        json={
            "name": "Provence Badminton",
            "description": "Tournois universitaires de badminton.",
        },
    )
    assert create_assoc.status_code == 201
    assoc_id = int(create_assoc.json()["id"])

    # Duplicate association name returns 409
    assert (
        client.post(
            "/associations",
            headers=admin_headers,
            json={"name": "Avignon Chess Club"},
        ).status_code
        == 409
    )

    # 2. Associate David (initially as member) and Emma (as member)
    add_david = client.post(
        f"/associations/{assoc_id}/members",
        headers=admin_headers,
        json={"user_id": david.id, "role_id": member_role.id},
    )
    assert add_david.status_code == 201
    assert add_david.json()["user"]["username"] == "david"
    assert add_david.json()["role"]["name"] == "member"

    assert (
        client.post(
            f"/associations/{assoc_id}/members",
            headers=admin_headers,
            json={"user_id": emma.id, "role_id": member_role.id},
        ).status_code
        == 201
    )

    # 3. Promote David to organizer in Provence Badminton
    promote_res = client.patch(
        f"/associations/{assoc_id}/members/{david.id}",
        headers=admin_headers,
        json={"role_id": organizer_role.id},
    )
    assert promote_res.status_code == 200
    assert promote_res.json()["role"]["name"] == "organizer"

    # 4. Verify persistence in PostgreSQL and via `/auth/me/memberships`
    persisted = db_session.get(Membership, {"user_id": david.id, "association_id": assoc_id})
    assert persisted is not None
    assert persisted.role_id == organizer_role.id

    david_memberships = client.get("/auth/me/memberships", headers=david_headers)
    assert david_memberships.status_code == 200
    roles_by_assoc = {m["association"]["name"]: m["role"]["name"] for m in david_memberships.json()}
    assert roles_by_assoc == {
        "Vaucluse eSport": "member",
        "Provence Badminton": "organizer",
    }


def test_demo_organizer_alice_can_manage_own_association_members(
    client: TestClient,
    db_session: Session,
) -> None:
    load_demo_data(db_session)
    alice_headers = _login_headers(client, "alice")

    chess_club = _association_by_name(db_session, "Avignon Chess Club")
    organizer_role = _role_by_name(db_session, "organizer")
    member_role = _role_by_name(db_session, "member")
    emma = _user_by_username(db_session, "emma")

    # Alice (organizer of Avignon Chess Club) updates her club's description
    upd_res = client.patch(
        f"/associations/{chess_club.id}",
        headers=alice_headers,
        json={"description": "Club d'échecs d'Avignon — ouvert à tous."},
    )
    assert upd_res.status_code == 200
    assert upd_res.json()["description"] == "Club d'échecs d'Avignon — ouvert à tous."

    # Alice adds Emma as a member of Avignon Chess Club
    add_res = client.post(
        f"/associations/{chess_club.id}/members",
        headers=alice_headers,
        json={"user_id": emma.id, "role_id": member_role.id},
    )
    assert add_res.status_code == 201

    # Alice promotes Emma to co-organizer, then removes her from the club
    role_res = client.patch(
        f"/associations/{chess_club.id}/members/{emma.id}",
        headers=alice_headers,
        json={"role_id": organizer_role.id},
    )
    assert role_res.status_code == 200
    assert role_res.json()["role"]["name"] == "organizer"

    rem_res = client.delete(
        f"/associations/{chess_club.id}/members/{emma.id}",
        headers=alice_headers,
    )
    assert rem_res.status_code == 204
    assert db_session.get(Membership, {"user_id": emma.id, "association_id": chess_club.id}) is None


def test_membership_conflicts_and_not_found_errors(
    client: TestClient,
    db_session: Session,
) -> None:
    load_demo_data(db_session)
    admin_headers = _login_headers(client, "admin")

    chess_club = _association_by_name(db_session, "Avignon Chess Club")
    member_role = _role_by_name(db_session, "member")
    chloe = _user_by_username(db_session, "chloe")
    emma = _user_by_username(db_session, "emma")

    # Chloe is already a member of Avignon Chess Club in the demo dataset -> 409
    assert (
        client.post(
            f"/associations/{chess_club.id}/members",
            headers=admin_headers,
            json={"user_id": chloe.id, "role_id": member_role.id},
        ).status_code
        == 409
    )

    # Non-existent user, role, association, or membership -> 404
    assert (
        client.post(
            f"/associations/{chess_club.id}/members",
            headers=admin_headers,
            json={"user_id": 999999, "role_id": member_role.id},
        ).status_code
        == 404
    )
    assert (
        client.post(
            f"/associations/{chess_club.id}/members",
            headers=admin_headers,
            json={"user_id": emma.id, "role_id": 999999},
        ).status_code
        == 404
    )
    assert (
        client.post(
            "/associations/999999/members",
            headers=admin_headers,
            json={"user_id": emma.id, "role_id": member_role.id},
        ).status_code
        == 404
    )
    assert (
        client.patch(
            f"/associations/{chess_club.id}/members/{emma.id}",
            headers=admin_headers,
            json={"role_id": member_role.id},
        ).status_code
        == 404
    )
    assert (
        client.delete(
            f"/associations/{chess_club.id}/members/{emma.id}",
            headers=admin_headers,
        ).status_code
        == 404
    )


# ---------------------------------------------------------------------------
# Access Control: Unauthorized (401) & Forbidden (403)
# ---------------------------------------------------------------------------


def test_unauthenticated_write_requests_are_refused(
    client: TestClient,
    db_session: Session,
) -> None:
    load_demo_data(db_session)
    chess_club = _association_by_name(db_session, "Avignon Chess Club")
    member_role = _role_by_name(db_session, "member")
    chloe = _user_by_username(db_session, "chloe")

    assert client.post("/roles", json={"name": "coach"}).status_code == 401
    assert client.patch(f"/roles/{member_role.id}", json={"name": "other"}).status_code == 401
    assert client.delete(f"/roles/{member_role.id}").status_code == 401

    assert client.post("/associations", json={"name": "Unauthorized Club"}).status_code == 401
    assert (
        client.patch(
            f"/associations/{chess_club.id}",
            json={"description": "hack"},
        ).status_code
        == 401
    )
    assert client.delete(f"/associations/{chess_club.id}").status_code == 401

    assert (
        client.post(
            f"/associations/{chess_club.id}/members",
            json={"user_id": chloe.id, "role_id": member_role.id},
        ).status_code
        == 401
    )
    assert (
        client.patch(
            f"/associations/{chess_club.id}/members/{chloe.id}",
            json={"role_id": member_role.id},
        ).status_code
        == 401
    )
    assert client.delete(f"/associations/{chess_club.id}/members/{chloe.id}").status_code == 401


def test_non_admins_and_other_association_organizers_are_forbidden(
    client: TestClient,
    db_session: Session,
) -> None:
    load_demo_data(db_session)

    # Demo personas:
    # - bob: organizer of Vaucluse eSport (NOT Avignon Chess Club)
    # - chloe: simple member of Avignon Chess Club
    # - david: simple member of Vaucluse eSport
    # - hugo: disabled demo user (is_active=False)
    bob_headers = _login_headers(client, "bob")
    chloe_headers = _login_headers(client, "chloe")
    david_headers = _login_headers(client, "david")
    hugo = _user_by_username(db_session, "hugo")
    hugo_headers = {"Authorization": f"Bearer {create_access_token(user_id=hugo.id)}"}

    chess_club = _association_by_name(db_session, "Avignon Chess Club")
    esport_club = _association_by_name(db_session, "Vaucluse eSport")
    organizer_role = _role_by_name(db_session, "organizer")
    member_role = _role_by_name(db_session, "member")
    chloe = _user_by_username(db_session, "chloe")
    emma = _user_by_username(db_session, "emma")

    # Global role & association creation/deletion are strictly superuser-only
    for headers in (bob_headers, chloe_headers, david_headers, hugo_headers):
        assert client.post("/roles", headers=headers, json={"name": "illicit"}).status_code == 403
        assert (
            client.post("/associations", headers=headers, json={"name": "Illicit"}).status_code
            == 403
        )
        assert client.delete(f"/associations/{esport_club.id}", headers=headers).status_code == 403

    # Neither Bob (organizer of Vaucluse eSport), Chloe (member of Avignon Chess Club),
    # David, nor Hugo can manage Avignon Chess Club
    for headers in (bob_headers, chloe_headers, david_headers, hugo_headers):
        assert (
            client.patch(
                f"/associations/{chess_club.id}",
                headers=headers,
                json={"description": "Unauthorized edit"},
            ).status_code
            == 403
        )
        assert (
            client.post(
                f"/associations/{chess_club.id}/members",
                headers=headers,
                json={"user_id": emma.id, "role_id": member_role.id},
            ).status_code
            == 403
        )
        assert (
            client.patch(
                f"/associations/{chess_club.id}/members/{chloe.id}",
                headers=headers,
                json={"role_id": organizer_role.id},
            ).status_code
            == 403
        )
        assert (
            client.delete(
                f"/associations/{chess_club.id}/members/{chloe.id}",
                headers=headers,
            ).status_code
            == 403
        )


def test_validation_and_association_deletion(
    client: TestClient,
    db_session: Session,
) -> None:
    load_demo_data(db_session)
    admin_headers = _login_headers(client, "admin")
    chess_club = _association_by_name(db_session, "Avignon Chess Club")
    alice = _user_by_username(db_session, "alice")

    assert client.post("/roles", headers=admin_headers, json={"name": "   "}).status_code == 422
    assert (
        client.post("/roles", headers=admin_headers, json={"name": "bad role!"}).status_code == 422
    )
    assert (
        client.post("/associations", headers=admin_headers, json={"name": "   "}).status_code == 422
    )

    # Deleting Avignon Chess Club cascades to its memberships
    del_res = client.delete(f"/associations/{chess_club.id}", headers=admin_headers)
    assert del_res.status_code == 204
    assert client.get(f"/associations/{chess_club.id}").status_code == 404
    assert (
        db_session.get(Membership, {"user_id": alice.id, "association_id": chess_club.id}) is None
    )


# ---------------------------------------------------------------------------
# CLI Admin Helpers
# ---------------------------------------------------------------------------


def test_cli_create_and_promote_admin_helpers(db_session: Session) -> None:
    load_demo_data(db_session)

    created = create_admin_user(
        db_session,
        email="cli_admin@example.com",
        username="cli_admin",
        password="AdminPassword123!",
        full_name="CLI Admin",
    )
    assert created.is_superuser is True
    assert created.is_active is True

    with pytest.raises(ValueError, match="already exists"):
        create_admin_user(
            db_session,
            email="cli_admin@example.com",
            username="other_name",
            password="AdminPassword123!",
        )

    emma = _user_by_username(db_session, "emma")
    assert emma.is_superuser is False

    promoted = promote_user_to_admin(db_session, "emma")
    assert promoted.id == emma.id
    assert emma.is_superuser is True

    with pytest.raises(LookupError):
        promote_user_to_admin(db_session, "nobody@example.com")

    parser = _build_parser()
    parsed = parser.parse_args(["promote-admin", "emma"])
    assert parsed.action == "promote-admin"
    assert parsed.identifier == "emma"
