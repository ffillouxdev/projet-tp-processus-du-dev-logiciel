"""Database lifecycle and administration helpers backed by Alembic migrations.

Usage (from backend/):
    uv run python -m app.db init    # apply every pending migration
    uv run python -m app.db reset   # drop the whole schema, then re-apply migrations
    uv run python -m app.db create-admin --email a@b.com --username admin --password Password123!
    uv run python -m app.db promote-admin <email_or_username>
"""

import argparse
import sys
from pathlib import Path

from alembic import command
from alembic.config import Config
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.user import User
from app.schemas.user import UserCreate
from app.security import get_password_hash

ALEMBIC_INI = Path(__file__).resolve().parent.parent / "alembic.ini"


def get_alembic_config(database_url: str | None = None) -> Config:
    """Build the Alembic config, optionally targeting another database than the settings one."""
    config = Config(str(ALEMBIC_INI))
    if database_url is not None:
        config.set_main_option("sqlalchemy.url", database_url.replace("%", "%%"))
    return config


def run_migrations(database_url: str | None = None) -> None:
    """Bring the database schema to the latest revision (creates it on an empty database)."""
    command.upgrade(get_alembic_config(database_url), "head")


def reset_database(database_url: str | None = None) -> None:
    """Revert every migration then re-apply them: all data is lost."""
    config = get_alembic_config(database_url)
    command.downgrade(config, "base")
    command.upgrade(config, "head")


def create_admin_user(
    db: Session,
    *,
    email: str,
    username: str,
    password: str,
    full_name: str | None = None,
) -> User:
    """Validate and create a new platform administrator (is_superuser=True)."""
    validated = UserCreate(
        email=email,
        username=username,
        password=password,
        full_name=full_name,
    )

    if db.scalar(select(User).where(User.email == validated.email)) is not None:
        raise ValueError(f"A user with email '{validated.email}' already exists")

    if db.scalar(select(User).where(User.username == validated.username)) is not None:
        raise ValueError(f"A user with username '{validated.username}' already exists")

    user = User(
        email=validated.email,
        username=validated.username,
        full_name=validated.full_name,
        hashed_password=get_password_hash(validated.password),
        is_active=True,
        is_superuser=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def promote_user_to_admin(db: Session, identifier: str) -> User:
    """Promote an existing user (matched by email or username) to platform administrator."""
    user = db.scalar(select(User).where((User.email == identifier) | (User.username == identifier)))
    if user is None:
        raise LookupError(f"No user found with email or username '{identifier}'")

    user.is_superuser = True
    db.commit()
    db.refresh(user)
    return user


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m app.db",
        description=(__doc__ or "").splitlines()[0],
    )
    subparsers = parser.add_subparsers(dest="action", required=True)

    subparsers.add_parser("init", help="Apply every pending Alembic migration")
    subparsers.add_parser("reset", help="Revert every migration then re-apply them (data loss)")

    create_parser = subparsers.add_parser(
        "create-admin",
        help="Create a new platform administrator account",
    )
    create_parser.add_argument("--email", required=True, help="Administrator email address")
    create_parser.add_argument("--username", required=True, help="Administrator username")
    create_parser.add_argument("--password", required=True, help="Administrator password")
    create_parser.add_argument("--full-name", default=None, help="Optional full name")

    promote_parser = subparsers.add_parser(
        "promote-admin",
        help="Promote an existing user to platform administrator",
    )
    promote_parser.add_argument("identifier", help="User email address or username")

    return parser


def main(argv: list[str] | None = None) -> None:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.action == "init":
        run_migrations()
        return

    if args.action == "reset":
        reset_database()
        return

    with SessionLocal() as db:
        try:
            if args.action == "create-admin":
                user = create_admin_user(
                    db,
                    email=args.email,
                    username=args.username,
                    password=args.password,
                    full_name=args.full_name,
                )
                print(f"Created administrator '{user.username}' ({user.email}) [id={user.id}].")
            elif args.action == "promote-admin":
                user = promote_user_to_admin(db, args.identifier)
                print(
                    f"Promoted user '{user.username}' ({user.email}) "
                    f"[id={user.id}] to administrator."
                )
        except (ValidationError, ValueError, LookupError) as exc:
            print(f"Error: {exc}", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    main()
