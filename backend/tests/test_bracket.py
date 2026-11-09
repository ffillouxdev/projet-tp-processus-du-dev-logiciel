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


def test_player_and_organizer_can_update_match_score_and_advance_bracket(
    client: TestClient,
    db_session: Session,
) -> None:
    load_demo_data(db_session)
    chess_club = _association_by_name(db_session, "Avignon Chess Club")
    alice_headers = _login_headers(client, "alice")
    chloe_headers = _login_headers(client, "chloe")

    users = [_user_by_username(db_session, u) for u in ("alice", "chloe")]
    tournament = Tournament(
        name="Tournoi Score 2 Joueurs",
        association_id=chess_club.id,
        status="open",
    )
    db_session.add(tournament)
    db_session.flush()
    for u in users:
        db_session.add(TournamentParticipant(tournament_id=tournament.id, user_id=u.id))
    db_session.commit()

    # Start tournament -> 1 finale match between alice and chloe
    start_res = client.post(f"/tournaments/{tournament.id}/start", headers=alice_headers)
    assert start_res.status_code == 200
    bracket = start_res.json()["bracket"]
    assert len(bracket) == 1
    final_match = bracket[0]

    # Player alice (player 1) reports score 3 - 1 -> awaiting confirmation
    alice_res = client.patch(
        f"/tournaments/{tournament.id}/matches/{final_match['id']}/score",
        json={"score_player1": 3, "score_player2": 1},
        headers=alice_headers,
    )
    assert alice_res.status_code == 200
    assert alice_res.json()["status"] == "awaiting_confirmation"
    assert alice_res.json()["advanced_to_next_match"] is False
    assert alice_res.json()["winner_id"] is None

    # Player chloe (player 2) reports identical score 3 - 1 -> consensus! Match completed
    score_res = client.patch(
        f"/tournaments/{tournament.id}/matches/{final_match['id']}/score",
        json={"score_player1": 3, "score_player2": 1},
        headers=chloe_headers,
    )
    assert score_res.status_code == 200
    body = score_res.json()
    assert body["winner_id"] == final_match["players"][0]["id"]
    assert body["tournament_status"] == "finished"
    assert body["advanced_to_next_match"] is False
    assert body["match"]["status"] == "completed"
    assert body["match"]["players"][0]["status"] == "winner"
    assert body["match"]["players"][1]["status"] == "loser"


def test_disputed_score_when_players_report_differing_scores(
    client: TestClient,
    db_session: Session,
) -> None:
    load_demo_data(db_session)
    chess_club = _association_by_name(db_session, "Avignon Chess Club")
    alice_headers = _login_headers(client, "alice")
    chloe_headers = _login_headers(client, "chloe")
    admin_headers = _login_headers(client, "admin")

    users = [_user_by_username(db_session, u) for u in ("alice", "chloe")]
    tournament = Tournament(
        name="Tournoi Litige Score",
        association_id=chess_club.id,
        status="open",
    )
    db_session.add(tournament)
    db_session.flush()
    for u in users:
        db_session.add(TournamentParticipant(tournament_id=tournament.id, user_id=u.id))
    db_session.commit()

    start_res = client.post(f"/tournaments/{tournament.id}/start", headers=alice_headers)
    assert start_res.status_code == 200
    match_id = start_res.json()["bracket"][0]["id"]

    # Player 1 claims 2 - 1
    p1_res = client.patch(
        f"/tournaments/{tournament.id}/matches/{match_id}/score",
        json={"score_player1": 2, "score_player2": 1},
        headers=alice_headers,
    )
    assert p1_res.status_code == 200
    assert p1_res.json()["status"] == "awaiting_confirmation"

    # Player 2 claims 0 - 3 (different) -> disputed!
    p2_res = client.patch(
        f"/tournaments/{tournament.id}/matches/{match_id}/score",
        json={"score_player1": 0, "score_player2": 3},
        headers=chloe_headers,
    )
    assert p2_res.status_code == 200
    assert p2_res.json()["status"] == "disputed"
    assert p2_res.json()["winner_id"] is None

    # Organizer/Admin arbitration overrides conflict
    final_p1_id = start_res.json()["bracket"][0]["players"][0]["id"]
    admin_res = client.patch(
        f"/tournaments/{tournament.id}/matches/{match_id}/score",
        json={"score_player1": 2, "score_player2": 0},
        headers=admin_headers,
    )
    assert admin_res.status_code == 200
    assert admin_res.json()["status"] == "completed"
    assert admin_res.json()["winner_id"] == final_p1_id
    assert admin_res.json()["tournament_status"] == "finished"


def test_score_validation_and_permissions(
    client: TestClient,
    db_session: Session,
) -> None:
    load_demo_data(db_session)
    chess_club = _association_by_name(db_session, "Avignon Chess Club")
    alice_headers = _login_headers(client, "alice")  # organizer
    bob_headers = _login_headers(client, "bob")  # organizer of another club

    users = [_user_by_username(db_session, u) for u in ("alice", "chloe", "david", "emma")]
    tournament = Tournament(
        name="Tournoi Validations Score",
        association_id=chess_club.id,
        status="open",
    )
    db_session.add(tournament)
    db_session.flush()
    for u in users:
        db_session.add(TournamentParticipant(tournament_id=tournament.id, user_id=u.id))
    db_session.commit()

    start_res = client.post(f"/tournaments/{tournament.id}/start", headers=alice_headers)
    assert start_res.status_code == 200
    bracket = start_res.json()["bracket"]

    # Round 1 matches
    r1_matches = [m for m in bracket if m["round_number"] == 1]
    m1 = r1_matches[0]
    p1_id = m1["players"][0]["id"]

    # Unknown user (bob) not in match and not admin of association -> 403
    res_forbidden = client.patch(
        f"/tournaments/{tournament.id}/matches/{m1['id']}/score",
        json={"score_player1": 2, "score_player2": 1},
        headers=bob_headers,
    )
    assert res_forbidden.status_code == 403

    # Negative score -> 422
    res_neg = client.patch(
        f"/tournaments/{tournament.id}/matches/{m1['id']}/score",
        json={"score_player1": -1, "score_player2": 2},
        headers=alice_headers,
    )
    assert res_neg.status_code == 422

    # Tie score -> 422
    res_tie = client.patch(
        f"/tournaments/{tournament.id}/matches/{m1['id']}/score",
        json={"score_player1": 2, "score_player2": 2},
        headers=alice_headers,
    )
    assert res_tie.status_code == 422

    # Score on a pending match in round 2 (final) -> 400
    final_match = next(m for m in bracket if m["round_number"] == 2)
    res_pending = client.patch(
        f"/tournaments/{tournament.id}/matches/{final_match['id']}/score",
        json={"score_player1": 2, "score_player2": 1},
        headers=alice_headers,
    )
    assert res_pending.status_code == 400
    assert "pending players" in res_pending.json()["detail"].lower()

    # Valid score on m1 by admin -> advances to final
    admin_headers = _login_headers(client, "admin")
    res_valid = client.patch(
        f"/tournaments/{tournament.id}/matches/{m1['id']}/score",
        json={"score_player1": 10, "score_player2": 5},
        headers=admin_headers,
    )
    assert res_valid.status_code == 200
    assert res_valid.json()["advanced_to_next_match"] is True
    assert res_valid.json()["winner_id"] == p1_id
