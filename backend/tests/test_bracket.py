from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Association, Tournament, TournamentParticipant, User
from app.seed import DEMO_PASSWORD, load_demo_data


def _login_headers(client: TestClient, username: str) -> dict[str, str]:
    response = client.post(
        "/auth/login",
        json={"identifier": username, "password": DEMO_PASSWORD},
    )
    assert response.status_code == 200, response.text
    token = str(response.json()["tokens"]["access_token"])
    return {"Authorization": f"Bearer {token}"}


def _association_by_name(db: Session, name: str) -> Association:
    return db.scalars(select(Association).where(Association.name == name)).one()


def _user_by_username(db: Session, username: str) -> User:
    return db.scalars(select(User).where(User.username == username)).one()


def test_organizer_can_start_tournament_and_generate_bracket_with_even_participants(
    client: TestClient,
    db_session: Session,
) -> None:
    load_demo_data(db_session)
    chess_club = _association_by_name(db_session, "Avignon Chess Club")
    alice_headers = _login_headers(client, "alice")  # organizer of chess club

    # Create a tournament with 4 registered participants
    users = [_user_by_username(db_session, u) for u in ("alice", "chloe", "david", "emma")]
    tournament = Tournament(
        name="Tournoi Test 4 Joueurs",
        association_id=chess_club.id,
        status="open",
    )
    db_session.add(tournament)
    db_session.flush()

    for u in users:
        db_session.add(TournamentParticipant(tournament_id=tournament.id, user_id=u.id))
    db_session.commit()

    # Launch the tournament
    res = client.post(f"/tournaments/{tournament.id}/start", headers=alice_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ongoing"
    assert data["total_participants"] == 4
    # Bracket of 4 players = 2 demi-finales + 1 finale = 3 matches
    assert data["total_matches"] == 3
    assert len(data["bracket"]) == 3

    # Check rounds
    rounds = [m["round"] for m in data["bracket"]]
    assert rounds == ["Demi-finales", "Demi-finales", "Finale"]

    # Check pairing for Round 1
    semi1 = data["bracket"][0]
    semi2 = data["bracket"][1]
    final = data["bracket"][2]

    assert semi1["next_match_id"] == final["id"]
    assert semi2["next_match_id"] == final["id"]

    # All 4 players are present in Round 1
    r1_player_ids = {
        semi1["players"][0]["id"],
        semi1["players"][1]["id"],
        semi2["players"][0]["id"],
        semi2["players"][1]["id"],
    }
    assert r1_player_ids == {u.id for u in users}

    # Public bracket endpoint returns the same bracket
    bracket_res = client.get(f"/tournaments/{tournament.id}/bracket")
    assert bracket_res.status_code == 200
    assert len(bracket_res.json()) == 3


def test_start_tournament_with_odd_participants_handles_byes(
    client: TestClient,
    db_session: Session,
) -> None:
    load_demo_data(db_session)
    chess_club = _association_by_name(db_session, "Avignon Chess Club")
    alice_headers = _login_headers(client, "alice")

    # Create a tournament with 3 participants (odd number)
    users = [_user_by_username(db_session, u) for u in ("alice", "chloe", "david")]
    tournament = Tournament(
        name="Tournoi Test 3 Joueurs",
        association_id=chess_club.id,
        status="open",
    )
    db_session.add(tournament)
    db_session.flush()

    for u in users:
        db_session.add(TournamentParticipant(tournament_id=tournament.id, user_id=u.id))
    db_session.commit()

    # Launch tournament
    res = client.post(f"/tournaments/{tournament.id}/start", headers=alice_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["total_participants"] == 3
    # Next power of 2 is 4 -> 3 matches (2 semi-finals, 1 final)
    assert data["total_matches"] == 3

    # Exactly 1 match in round 1 has a BYE
    round1_matches = [m for m in data["bracket"] if m["round"] == "Demi-finales"]
    bye_matches = [m for m in round1_matches if any(p["name"] == "BYE" for p in m["players"])]
    assert len(bye_matches) == 1

    bye_match = bye_matches[0]
    # The bye match should be marked completed with an automatic winner
    assert bye_match["status"] == "completed"
    assert bye_match["winner_id"] is not None

    # The winner of the bye match is already propagated to the final
    final_match = [m for m in data["bracket"] if m["round"] == "Finale"][0]
    final_player_ids = {p["id"] for p in final_match["players"] if p["id"] is not None}
    assert bye_match["winner_id"] in final_player_ids


def test_start_tournament_rejects_insufficient_participants(
    client: TestClient,
    db_session: Session,
) -> None:
    load_demo_data(db_session)
    chess_club = _association_by_name(db_session, "Avignon Chess Club")
    alice_headers = _login_headers(client, "alice")
    alice = _user_by_username(db_session, "alice")

    # Only 1 participant
    tournament = Tournament(
        name="Tournoi Solitaire",
        association_id=chess_club.id,
        status="open",
    )
    db_session.add(tournament)
    db_session.flush()
    db_session.add(TournamentParticipant(tournament_id=tournament.id, user_id=alice.id))
    db_session.commit()

    res = client.post(f"/tournaments/{tournament.id}/start", headers=alice_headers)
    assert res.status_code == 400
    assert "at least 2 participants" in res.json()["detail"].lower()


def test_start_tournament_permission_checks(
    client: TestClient,
    db_session: Session,
) -> None:
    load_demo_data(db_session)
    chess_club = _association_by_name(db_session, "Avignon Chess Club")

    bob_headers = _login_headers(client, "bob")  # organizer of Vaucluse eSport (different club)
    chloe_headers = _login_headers(client, "chloe")  # simple member of chess club
    admin_headers = _login_headers(client, "admin")  # platform superuser

    users = [_user_by_username(db_session, u) for u in ("alice", "chloe")]
    tournament = Tournament(
        name="Tournoi Droits",
        association_id=chess_club.id,
        status="open",
    )
    db_session.add(tournament)
    db_session.flush()
    for u in users:
        db_session.add(TournamentParticipant(tournament_id=tournament.id, user_id=u.id))
    db_session.commit()

    # Anonymous -> 401
    assert client.post(f"/tournaments/{tournament.id}/start").status_code == 401

    # Chloe (simple member) -> 403
    assert (
        client.post(f"/tournaments/{tournament.id}/start", headers=chloe_headers).status_code == 403
    )

    # Bob (organizer of another club) -> 403
    assert (
        client.post(f"/tournaments/{tournament.id}/start", headers=bob_headers).status_code == 403
    )

    # Admin (superuser) -> 200
    res = client.post(f"/tournaments/{tournament.id}/start", headers=admin_headers)
    assert res.status_code == 200

    # Cannot start an already ongoing or finished tournament -> 409
    res_ongoing = client.post(f"/tournaments/{tournament.id}/start", headers=admin_headers)
    assert res_ongoing.status_code == 409
    assert "already ongoing" in res_ongoing.json()["detail"].lower()
