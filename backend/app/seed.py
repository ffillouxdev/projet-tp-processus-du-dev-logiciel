"""Load the demonstration dataset (demo environment only).

Usage (from backend/):
    uv run python -m app.seed    # or: make db-seed

The load is idempotent: every record is looked up by its natural key (username, role name,
association name, tournament name inside its association) and updated in place, so running it
again never creates duplicates. Demo accounts get their password reset to DEMO_PASSWORD.
"""

import argparse
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.database import SessionLocal
from app.models import Association, Membership, Role, Tournament, TournamentParticipant, User
from app.security import get_password_hash

# Shared by every demo account. Never reuse it outside the demo environment.
DEMO_PASSWORD = "Demo1234!"
DEMO_EMAIL_DOMAIN = "demo.example.com"

FORBIDDEN_ENVIRONMENTS = {"production"}

ROLES = {
    "organizer": "Crée et gère les tournois de son association.",
    "member": "Membre d'une association : voit ses tournois, y compris les brouillons.",
}

ASSOCIATIONS = {
    "Avignon Chess Club": "Club d'échecs avignonnais, tournois rapides et blitz.",
    "Vaucluse eSport": "Association de sport électronique du Grand Avignon.",
}


@dataclass(frozen=True)
class DemoUser:
    username: str
    full_name: str
    is_superuser: bool = False
    is_active: bool = True


USERS = [
    DemoUser("admin", "Admin Démo", is_superuser=True),
    DemoUser("alice", "Alice Martin"),
    DemoUser("bob", "Bob Durand"),
    DemoUser("chloe", "Chloé Bernard"),
    DemoUser("david", "David Petit"),
    DemoUser("emma", "Emma Robert"),
    DemoUser("hugo", "Hugo Moreau", is_active=False),
]

# (username, association, role)
MEMBERSHIPS = [
    ("alice", "Avignon Chess Club", "organizer"),
    ("chloe", "Avignon Chess Club", "member"),
    ("bob", "Vaucluse eSport", "organizer"),
    ("david", "Vaucluse eSport", "member"),
    ("emma", "Vaucluse eSport", "member"),
]


@dataclass(frozen=True)
class DemoTournament:
    association: str
    name: str
    description: str
    status: str
    start_in_days: int
    duration_days: int
    max_participants: int | None
    participants: tuple[str, ...] = ()


# Draft tournaments have no participants: registration only opens once they are published.
TOURNAMENTS = [
    DemoTournament(
        "Avignon Chess Club",
        "Blitz d'automne",
        "Tournoi blitz 5+0 terminé, résultats consultables.",
        "finished",
        -30,
        1,
        16,
        ("chloe", "david", "emma"),
    ),
    DemoTournament(
        "Avignon Chess Club",
        "Open rapide d'Avignon",
        "Tournoi rapide 15+10 en cours, ouvert à tous les joueurs.",
        "ongoing",
        -1,
        3,
        32,
        ("chloe", "emma"),
    ),
    DemoTournament(
        "Avignon Chess Club",
        "Championnat interne",
        "Brouillon visible uniquement par les membres du club.",
        "draft",
        45,
        2,
        8,
    ),
    DemoTournament(
        "Vaucluse eSport",
        "Coupe Rocket League 2v2",
        "Inscriptions ouvertes, places limitées.",
        "open",
        14,
        1,
        8,
        ("david", "chloe"),
    ),
    DemoTournament(
        "Vaucluse eSport",
        "Ligue Smash Bros",
        "Ligue sur plusieurs semaines, sans limite de participants.",
        "open",
        21,
        28,
        None,
        ("emma",),
    ),
    DemoTournament(
        "Vaucluse eSport",
        "LAN de printemps",
        "Brouillon en préparation par l'organisateur.",
        "draft",
        120,
        2,
        64,
    ),
]


@dataclass(frozen=True)
class SeedSummary:
    roles: int
    associations: int
    users: int
    memberships: int
    tournaments: int
    participants: int


def demo_email(username: str) -> str:
    return f"{username}@{DEMO_EMAIL_DOMAIN}"


def _upsert_roles(db: Session) -> dict[str, Role]:
    roles: dict[str, Role] = {}
    for name, description in ROLES.items():
        role = db.scalar(select(Role).where(Role.name == name)) or Role(name=name)
        role.description = description
        db.add(role)
        roles[name] = role
    return roles


def _upsert_associations(db: Session) -> dict[str, Association]:
    associations: dict[str, Association] = {}
    for name, description in ASSOCIATIONS.items():
        association = db.scalar(select(Association).where(Association.name == name))
        association = association or Association(name=name)
        association.description = description
        db.add(association)
        associations[name] = association
    return associations


def _upsert_users(db: Session) -> dict[str, User]:
    hashed_password = get_password_hash(DEMO_PASSWORD)
    users: dict[str, User] = {}
    for demo in USERS:
        user = db.scalar(select(User).where(User.username == demo.username))
        user = user or User(username=demo.username)
        user.email = demo_email(demo.username)
        user.full_name = demo.full_name
        user.hashed_password = hashed_password
        user.is_active = demo.is_active
        user.is_superuser = demo.is_superuser
        db.add(user)
        users[demo.username] = user
    return users


def _upsert_memberships(
    db: Session,
    users: dict[str, User],
    associations: dict[str, Association],
    roles: dict[str, Role],
) -> None:
    for username, association_name, role_name in MEMBERSHIPS:
        user, association = users[username], associations[association_name]
        membership = db.get(Membership, (user.id, association.id))
        membership = membership or Membership(user=user, association=association)
        membership.role = roles[role_name]
        db.add(membership)


def _upsert_tournaments(
    db: Session, users: dict[str, User], associations: dict[str, Association]
) -> None:
    today = datetime.now(UTC).replace(hour=9, minute=0, second=0, microsecond=0)
    for demo in TOURNAMENTS:
        association = associations[demo.association]
        tournament = db.scalar(
            select(Tournament).where(
                Tournament.association_id == association.id, Tournament.name == demo.name
            )
        )
        tournament = tournament or Tournament(name=demo.name, association=association)
        tournament.description = demo.description
        tournament.status = demo.status
        tournament.max_participants = demo.max_participants
        tournament.start_date = today + timedelta(days=demo.start_in_days)
        tournament.end_date = tournament.start_date + timedelta(days=demo.duration_days)
        db.add(tournament)
        db.flush()

        for username in demo.participants:
            user = users[username]
            if db.get(TournamentParticipant, (tournament.id, user.id)) is None:
                db.add(TournamentParticipant(tournament=tournament, user=user))


def load_demo_data(db: Session) -> SeedSummary:
    """Create or update the demo dataset in the given session (the caller commits)."""
    roles = _upsert_roles(db)
    associations = _upsert_associations(db)
    users = _upsert_users(db)
    db.flush()
    _upsert_memberships(db, users, associations, roles)
    _upsert_tournaments(db, users, associations)
    db.flush()
    return SeedSummary(
        roles=len(ROLES),
        associations=len(ASSOCIATIONS),
        users=len(USERS),
        memberships=len(MEMBERSHIPS),
        tournaments=len(TOURNAMENTS),
        participants=sum(len(t.participants) for t in TOURNAMENTS),
    )


def check_environment(environment: str) -> None:
    if environment.lower() in FORBIDDEN_ENVIRONMENTS:
        raise SystemExit(
            f"Refusing to load demo data in ENVIRONMENT={environment}: "
            "demo accounts share a public password."
        )


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m app.seed", description=__doc__.splitlines()[0])
    parser.parse_args()
    check_environment(settings.ENVIRONMENT)

    with SessionLocal() as db, db.begin():
        summary = load_demo_data(db)

    print(
        f"Demo data loaded: {summary.users} users, {summary.roles} roles, "
        f"{summary.associations} associations, {summary.memberships} memberships, "
        f"{summary.tournaments} tournaments, {summary.participants} registrations."
    )
    print(f"Every demo account uses the password {DEMO_PASSWORD!r} (demo environment only).")


if __name__ == "__main__":
    main()
