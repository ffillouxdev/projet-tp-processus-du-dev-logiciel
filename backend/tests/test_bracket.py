from typing import Any

import pytest
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
    first_match = start_res.json()["bracket"][0]
    match_id = first_match["id"]
    p1_is_alice = first_match["players"][0]["id"] == users[0].id

    # Player 1 reports 2 - 1 (from p1's perspective: p1 scored 2, p2 scored 1)
    p1_headers = alice_headers if p1_is_alice else chloe_headers
    p2_headers = chloe_headers if p1_is_alice else alice_headers

    p1_res = client.patch(
        f"/tournaments/{tournament.id}/matches/{match_id}/score",
        json={"score_player1": 2, "score_player2": 1},
        headers=p1_headers,
    )
    assert p1_res.status_code == 200
    assert p1_res.json()["status"] == "awaiting_confirmation"

    # Player 2 reports 0 - 3 (different) -> disputed!
    p2_res = client.patch(
        f"/tournaments/{tournament.id}/matches/{match_id}/score",
        json={"score_player1": 0, "score_player2": 3},
        headers=p2_headers,
    )
    assert p2_res.status_code == 200
    assert p2_res.json()["status"] == "disputed"
    assert p2_res.json()["winner_id"] is None

    # Check alert / dispute listing via GET /tournaments/{id}/disputes (organizer Alice)
    disputes_res = client.get(
        f"/tournaments/{tournament.id}/disputes",
        headers=alice_headers,
    )
    assert disputes_res.status_code == 200
    disputes = disputes_res.json()
    assert len(disputes) == 1
    assert disputes[0]["match_id"] == match_id
    assert disputes[0]["status"] == "disputed"
    assert disputes[0]["player1_reported_score"] == [2, 1]
    assert disputes[0]["player2_reported_score"] == [0, 3]

    # Dispute is also visible via GET /tournaments/{id}/bracket?status=disputed
    bracket_disputed = client.get(
        f"/tournaments/{tournament.id}/bracket?status=disputed",
        headers=alice_headers,
    )
    assert bracket_disputed.status_code == 200
    assert len(bracket_disputed.json()) == 1
    assert bracket_disputed.json()[0]["id"] == match_id

    # Non-organizer cannot view /disputes -> 403
    disputes_forbidden = client.get(
        f"/tournaments/{tournament.id}/disputes",
        headers=chloe_headers,
    )
    assert disputes_forbidden.status_code == 403

    # Resolve dispute via explicit POST /resolve-dispute endpoint with reason
    final_p1_id = start_res.json()["bracket"][0]["players"][0]["id"]
    resolve_res = client.post(
        f"/tournaments/{tournament.id}/matches/{match_id}/resolve-dispute",
        json={"score_player1": 2, "score_player2": 0, "reason": "Arbitrage vidéo"},
        headers=alice_headers,
    )
    assert resolve_res.status_code == 200
    assert resolve_res.json()["status"] == "completed"
    assert resolve_res.json()["winner_id"] == final_p1_id
    assert resolve_res.json()["tournament_status"] == "finished"
    assert "Arbitrage vidéo" in resolve_res.json()["message"]

    # /disputes is now empty
    empty_disputes = client.get(
        f"/tournaments/{tournament.id}/disputes",
        headers=alice_headers,
    )
    assert len(empty_disputes.json()) == 0


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


# ---------------------------------------------------------------------------
# Closing the event (US-204)
# ---------------------------------------------------------------------------


def _start_tournament_with(
    client: TestClient,
    db_session: Session,
    usernames: tuple[str, ...],
    headers: dict[str, str],
) -> tuple[Tournament, list[dict[str, Any]]]:
    chess_club = _association_by_name(db_session, "Avignon Chess Club")
    tournament = Tournament(
        name=f"Tournoi Clôture {len(usernames)}",
        association_id=chess_club.id,
        status="open",
    )
    db_session.add(tournament)
    db_session.flush()
    for username in usernames:
        user = _user_by_username(db_session, username)
        db_session.add(TournamentParticipant(tournament_id=tournament.id, user_id=user.id))
    db_session.commit()

    res = client.post(f"/tournaments/{tournament.id}/start", headers=headers)
    assert res.status_code == 200, res.text
    return tournament, res.json()["bracket"]


def _report(
    client: TestClient,
    tournament: Tournament,
    match_id: int,
    headers: dict[str, str],
    scores: tuple[int, int] = (2, 1),
) -> Any:
    return client.patch(
        f"/tournaments/{tournament.id}/matches/{match_id}/score",
        json={"score_player1": scores[0], "score_player2": scores[1]},
        headers=headers,
    )


def test_validating_the_final_closes_tournament_and_exposes_winner(
    client: TestClient,
    db_session: Session,
) -> None:
    load_demo_data(db_session)
    admin_headers = _login_headers(client, "admin")
    tournament, bracket = _start_tournament_with(
        client, db_session, ("alice", "chloe", "david", "emma"), admin_headers
    )
    semis = [m for m in bracket if m["round_number"] == 1]
    final = next(m for m in bracket if m["round_number"] == 2)

    # Semi-finals do not close the tournament
    for semi in semis:
        res = _report(client, tournament, semi["id"], admin_headers)
        assert res.status_code == 200
        assert res.json()["tournament_status"] == "ongoing"
        assert res.json()["tournament_winner_id"] is None

    detail = client.get(f"/tournaments/{tournament.id}").json()
    assert detail["status"] == "ongoing"
    assert detail["winner_id"] is None
    assert detail["winner"] is None

    # The final (player2 wins) closes the tournament
    res = _report(client, tournament, final["id"], admin_headers, scores=(0, 3))
    assert res.status_code == 200
    champion_id = semis[1]["players"][0]["id"]
    assert res.json()["tournament_status"] == "finished"
    assert res.json()["winner_id"] == champion_id
    assert res.json()["tournament_winner_id"] == champion_id

    # The winner is shown publicly, in the detail and in the list
    detail = client.get(f"/tournaments/{tournament.id}").json()
    assert detail["status"] == "finished"
    assert detail["winner_id"] == champion_id
    assert detail["winner"]["id"] == champion_id
    assert detail["winner"]["username"]

    listed = client.get("/tournaments", params={"status": "finished"}).json()
    assert next(t for t in listed if t["id"] == tournament.id)["winner_id"] == champion_id


def test_finished_tournament_results_are_locked(
    client: TestClient,
    db_session: Session,
) -> None:
    load_demo_data(db_session)
    admin_headers = _login_headers(client, "admin")
    tournament, bracket = _start_tournament_with(
        client, db_session, ("alice", "chloe"), admin_headers
    )
    final = bracket[0]
    assert _report(client, tournament, final["id"], admin_headers).status_code == 200

    # Rewriting the final score after closure is refused, winner unchanged
    res = _report(client, tournament, final["id"], admin_headers, scores=(0, 5))
    assert res.status_code == 409
    assert res.json()["detail"] == "Scores can only be recorded while the tournament is ongoing"
    detail = client.get(f"/tournaments/{tournament.id}").json()
    assert detail["winner_id"] == final["players"][0]["id"]


def test_reopening_a_finished_tournament_clears_its_winner(
    client: TestClient,
    db_session: Session,
) -> None:
    load_demo_data(db_session)
    admin_headers = _login_headers(client, "admin")
    tournament, bracket = _start_tournament_with(
        client, db_session, ("alice", "chloe"), admin_headers
    )
    assert _report(client, tournament, bracket[0]["id"], admin_headers).status_code == 200

    res = client.patch(
        f"/tournaments/{tournament.id}", json={"status": "ongoing"}, headers=admin_headers
    )
    assert res.status_code == 200
    assert res.json()["status"] == "ongoing"
    assert res.json()["winner_id"] is None


def test_published_tournament_without_matches_has_no_winner(
    client: TestClient,
    db_session: Session,
) -> None:
    load_demo_data(db_session)
    smash = db_session.scalars(
        select(Tournament).where(Tournament.name == "Ligue Smash Bros")
    ).one()

    detail = client.get(f"/tournaments/{smash.id}").json()
    assert detail["winner_id"] is None
    assert detail["winner"] is None


@pytest.mark.parametrize("player_count", [5, 6, 7])
def test_bracket_with_byes_can_be_played_until_closure(
    client: TestClient,
    db_session: Session,
    player_count: int,
) -> None:
    load_demo_data(db_session)
    admin_headers = _login_headers(client, "admin")
    usernames = ["alice", "bob", "chloe", "david", "emma"]
    for idx in range(player_count - len(usernames)):
        username = f"extra{idx}"
        db_session.add(
            User(
                username=username,
                email=f"{username}@example.com",
                hashed_password="not-used",
            )
        )
        usernames.append(username)
    db_session.flush()
    tournament, bracket = _start_tournament_with(
        client, db_session, tuple(usernames), admin_headers
    )

    # No round-1 match opposes two BYEs
    for match in (m for m in bracket if m["round_number"] == 1):
        assert any(p["id"] is not None for p in match["players"]), match

    # Every playable match can be scored until the final closes the tournament
    for _ in range(len(bracket)):
        current = client.get(f"/tournaments/{tournament.id}/bracket").json()
        playable = [
            m
            for m in current
            if m["status"] != "completed" and all(p["id"] is not None for p in m["players"])
        ]
        if not playable:
            break
        res = _report(client, tournament, playable[0]["id"], admin_headers)
        assert res.status_code == 200, res.text

    detail = client.get(f"/tournaments/{tournament.id}").json()
    assert detail["status"] == "finished"
    assert detail["winner_id"] in {p.id for p in db_session.scalars(select(User))}


def test_final_confirmed_by_both_players_closes_tournament(
    client: TestClient,
    db_session: Session,
) -> None:
    load_demo_data(db_session)
    alice_headers = _login_headers(client, "alice")
    chloe_headers = _login_headers(client, "chloe")
    tournament, bracket = _start_tournament_with(
        client, db_session, ("alice", "chloe"), alice_headers
    )
    final = bracket[0]

    # First report only awaits the opponent's confirmation
    res = _report(client, tournament, final["id"], alice_headers, scores=(3, 1))
    assert res.status_code == 200
    assert res.json()["status"] == "awaiting_confirmation"
    assert res.json()["tournament_status"] == "ongoing"
    assert res.json()["tournament_winner_id"] is None

    # Matching report from the opponent validates the final and closes the tournament
    res = _report(client, tournament, final["id"], chloe_headers, scores=(3, 1))
    assert res.status_code == 200
    champion_id = final["players"][0]["id"]
    assert res.json()["tournament_status"] == "finished"
    assert res.json()["tournament_winner_id"] == champion_id
    assert client.get(f"/tournaments/{tournament.id}").json()["winner"]["id"] == champion_id


def test_tournament_websocket_connection_and_realtime_broadcast(
    client: TestClient,
    db_session: Session,
) -> None:
    load_demo_data(db_session)
    alice_headers = _login_headers(client, "alice")
    chloe_headers = _login_headers(client, "chloe")
    tournament, bracket = _start_tournament_with(
        client, db_session, ("alice", "chloe"), alice_headers
    )
    final_match = bracket[0]

    # Connect WebSocket client to tournament room
    with client.websocket_connect(f"/tournaments/{tournament.id}/ws") as websocket:
        # Initial bracket is received upon connection
        initial_msg = websocket.receive_json()
        assert initial_msg["type"] == "initial_bracket"
        assert initial_msg["tournament_id"] == tournament.id
        assert len(initial_msg["bracket"]) == 1

        # Ping pong test
        websocket.send_text("ping")
        assert websocket.receive_text() == "pong"

        # Determine if alice is player 1 or player 2 in the match
        p1_is_alice = final_match["players"][0]["id"] == _user_by_username(db_session, "alice").id

        # First player reports score (awaiting confirmation) -> broadcast event
        reporter1 = alice_headers if p1_is_alice else chloe_headers
        reporter2 = chloe_headers if p1_is_alice else alice_headers

        res1 = _report(client, tournament, final_match["id"], reporter1, scores=(3, 1))
        assert res1.status_code == 200

        update_msg1 = websocket.receive_json()
        assert update_msg1["type"] == "bracket_updated"
        assert update_msg1["tournament_id"] == tournament.id
        assert update_msg1["bracket"][0]["player1_reported_score"] == [3, 1]
        assert update_msg1["bracket"][0]["status"] == "awaiting_confirmation"

        # Second player confirms identical score -> match completed & tournament finished
        res2 = _report(client, tournament, final_match["id"], reporter2, scores=(3, 1))
        assert res2.status_code == 200

        update_msg2 = websocket.receive_json()
        assert update_msg2["type"] == "bracket_updated"
        assert update_msg2["status"] == "finished"
        assert update_msg2["bracket"][0]["status"] == "completed"
        assert update_msg2["winner_id"] is not None
