import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Association, Membership, Role, Tournament, TournamentParticipant, User
from app.models.role import DEFAULT_ROLE_NAME


def _make_user(db: Session, username: str = "modeluser") -> User:
    user = User(email=f"{username}@example.com", username=username, hashed_password="hash")
    db.add(user)
    db.flush()
    return user


def test_new_user_gets_the_default_participant_role(db_session: Session):
    user = _make_user(db_session)
    db_session.refresh(user)

    assert user.role.name == DEFAULT_ROLE_NAME


def test_user_global_role_can_be_changed(db_session: Session):
    admin = Role(name="admin")
    user = User(email="a@example.com", username="adminuser", hashed_password="hash", role=admin)
    db_session.add(user)
    db_session.flush()

    assert user.role_id == admin.id
    assert admin.users == [user]


def test_default_role_cannot_be_deleted_while_assigned(db_session: Session):
    _make_user(db_session)

    with pytest.raises(IntegrityError), db_session.begin_nested():
        db_session.execute(Role.__table__.delete().where(Role.name == DEFAULT_ROLE_NAME))


def test_user_has_a_role_inside_an_association(db_session: Session):
    user = _make_user(db_session)
    club = Association(name="Chess Club")
    organizer = Role(name="organizer", description="Organizes the association tournaments")
    db_session.add(Membership(user=user, association=club, role=organizer))
    db_session.flush()

    membership = user.memberships[0]
    assert membership.association.name == "Chess Club"
    assert membership.role.name == "organizer"
    assert membership.joined_at is not None
    assert club.memberships == [membership]


def test_user_can_join_an_association_only_once(db_session: Session):
    user = _make_user(db_session)
    club = Association(name="Go Club")
    member = Role(name="member")
    db_session.add(Membership(user=user, association=club, role=member))
    db_session.flush()

    with pytest.raises(IntegrityError), db_session.begin_nested():
        db_session.execute(
            Membership.__table__.insert().values(
                user_id=user.id, association_id=club.id, role_id=member.id
            )
        )


def test_deleting_user_cascades_to_memberships_and_participations(db_session: Session):
    user = _make_user(db_session)
    club = Association(name="Esport League")
    tournament = Tournament(name="Cup", association=club)
    db_session.add_all(
        [
            Membership(user=user, association=club, role=Role(name="player")),
            TournamentParticipant(user=user, tournament=tournament),
        ]
    )
    db_session.flush()

    db_session.delete(user)
    db_session.flush()

    assert db_session.scalars(select(Membership)).all() == []
    assert db_session.scalars(select(TournamentParticipant)).all() == []
    assert db_session.scalar(select(Tournament).where(Tournament.name == "Cup")) is not None


def test_role_in_use_cannot_be_deleted(db_session: Session):
    user = _make_user(db_session)
    referee = Role(name="referee")
    db_session.add(Membership(user=user, association=Association(name="Ref Club"), role=referee))
    db_session.flush()

    with pytest.raises(IntegrityError), db_session.begin_nested():
        db_session.execute(Role.__table__.delete().where(Role.id == referee.id))


def test_user_participates_in_tournaments(db_session: Session):
    alice = _make_user(db_session, "alice")
    bob = _make_user(db_session, "bob")
    tournament = Tournament(name="Spring Open", association=Association(name="Tennis Club"))
    db_session.add_all(
        [
            TournamentParticipant(user=alice, tournament=tournament),
            TournamentParticipant(user=bob, tournament=tournament),
        ]
    )
    db_session.flush()

    assert {p.user.username for p in tournament.participants} == {"alice", "bob"}
    assert alice.participations[0].tournament is tournament
    assert alice.participations[0].registered_at is not None


def test_tournament_defaults_to_draft_status(db_session: Session):
    association = Association(name="Chess Federation")
    tournament = Tournament(name="Winter Open", association=association)
    db_session.add(tournament)
    db_session.flush()
    db_session.refresh(tournament)

    assert tournament.status == "draft"
    assert tournament.max_participants is None
    assert tournament.created_at is not None
    assert association.tournaments == [tournament]


def test_deleting_association_cascades_to_tournaments(db_session: Session):
    association = Association(name="Badminton Club")
    association.tournaments.append(Tournament(name="Cup"))
    db_session.add(association)
    db_session.flush()

    db_session.delete(association)
    db_session.flush()

    assert db_session.scalars(select(Tournament)).all() == []
