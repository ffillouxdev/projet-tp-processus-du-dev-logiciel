import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Association, Membership, Role, Tournament, TournamentParticipant, User
from app.seed import (
    DEMO_PASSWORD,
    MEMBERSHIPS,
    TOURNAMENTS,
    USERS,
    check_environment,
    demo_email,
    load_demo_data,
)

MODELS = (Association, Membership, Role, Tournament, TournamentParticipant, User)


def _counts(db: Session) -> dict[str, int]:
    return {
        model.__name__: db.scalar(select(func.count()).select_from(model)) or 0 for model in MODELS
    }


def test_load_creates_the_demo_dataset(db_session: Session) -> None:
    summary = load_demo_data(db_session)

    assert _counts(db_session) == {
        "Association": summary.associations,
        "Membership": summary.memberships,
        "Role": summary.roles,
        "Tournament": summary.tournaments,
        "TournamentParticipant": summary.participants,
        "User": summary.users,
    }
    assert summary.tournaments >= 2
    assert {t.status for t in TOURNAMENTS} >= {"draft", "open", "ongoing", "finished"}


def test_reloading_does_not_create_duplicates(db_session: Session) -> None:
    load_demo_data(db_session)
    first = _counts(db_session)

    load_demo_data(db_session)

    assert _counts(db_session) == first


def test_reloading_restores_modified_demo_records(db_session: Session) -> None:
    load_demo_data(db_session)
    alice = db_session.scalars(select(User).where(User.username == "alice")).one()
    alice.full_name = "Changed"
    alice.is_active = False
    db_session.flush()

    load_demo_data(db_session)

    assert alice.full_name == "Alice Martin"
    assert alice.is_active is True


def test_demo_accounts_can_log_in(client: TestClient, db_session: Session) -> None:
    load_demo_data(db_session)

    for demo in USERS:
        response = client.post(
            "/auth/login", json={"identifier": demo.username, "password": DEMO_PASSWORD}
        )
        assert response.status_code == (200 if demo.is_active else 403), demo.username
        if demo.is_active:
            assert response.json()["user"]["email"] == demo_email(demo.username)


def test_dataset_is_consistent_with_access_rules(db_session: Session) -> None:
    load_demo_data(db_session)

    admins = db_session.scalars(select(User).where(User.is_superuser)).all()
    assert [u.username for u in admins] == ["admin"]

    # Every association has an organizer; every seeded role is assigned at least once (1,n)
    for association in db_session.scalars(select(Association)):
        assert "organizer" in {m.role.name for m in association.memberships}
    assert {role for _, _, role in MEMBERSHIPS} == {
        r.name for r in db_session.scalars(select(Role))
    }

    for tournament in db_session.scalars(select(Tournament)):
        registered = [p.user for p in tournament.participants]
        if tournament.status == "draft":
            assert registered == [], tournament.name
        if tournament.max_participants is not None:
            assert len(registered) <= tournament.max_participants
        assert all(user.is_active for user in registered)
        assert tournament.start_date is not None and tournament.end_date is not None
        assert tournament.start_date <= tournament.end_date


@pytest.mark.parametrize("environment", ["production", "PRODUCTION"])
def test_loading_is_refused_in_production(environment: str) -> None:
    with pytest.raises(SystemExit):
        check_environment(environment)


@pytest.mark.parametrize("environment", ["development", "demo", "test"])
def test_loading_is_allowed_outside_production(environment: str) -> None:
    check_environment(environment)
