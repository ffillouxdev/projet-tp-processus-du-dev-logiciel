from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Association, Role, Tournament, User, user_roles


def _make_user(db: Session) -> User:
    user = User(email="model@example.com", username="modeluser", hashed_password="hash")
    db.add(user)
    db.flush()
    return user


def test_user_roles_many_to_many(db_session: Session):
    user = _make_user(db_session)
    admin = Role(name="admin", description="Platform administrator")
    organizer = Role(name="organizer")
    user.roles.extend([admin, organizer])
    db_session.flush()

    db_session.refresh(admin)
    assert {role.name for role in user.roles} == {"admin", "organizer"}
    assert admin.users == [user]


def test_deleting_user_cascades_to_user_roles(db_session: Session):
    user = _make_user(db_session)
    user.roles.append(Role(name="player"))
    db_session.flush()

    db_session.delete(user)
    db_session.flush()

    assert db_session.scalars(select(user_roles.c.user_id)).all() == []
    assert db_session.scalar(select(Role).where(Role.name == "player")) is not None


def test_tournament_defaults_to_draft_status(db_session: Session):
    association = Association(name="Chess Club")
    tournament = Tournament(name="Spring Open", association=association)
    db_session.add(tournament)
    db_session.flush()
    db_session.refresh(tournament)

    assert tournament.status == "draft"
    assert tournament.max_participants is None
    assert tournament.created_at is not None
    assert association.tournaments == [tournament]


def test_deleting_association_cascades_to_tournaments(db_session: Session):
    association = Association(name="Esport League")
    association.tournaments.append(Tournament(name="Cup"))
    db_session.add(association)
    db_session.flush()

    db_session.delete(association)
    db_session.flush()

    assert db_session.scalars(select(Tournament)).all() == []
