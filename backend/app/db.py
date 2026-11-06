"""Database lifecycle helpers backed by Alembic migrations.

Usage (from backend/):
    uv run python -m app.db init    # apply every pending migration
    uv run python -m app.db reset   # drop the whole schema, then re-apply migrations
"""

import argparse
from pathlib import Path

from alembic import command
from alembic.config import Config

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


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m app.db", description=__doc__.splitlines()[0])
    parser.add_argument("action", choices=["init", "reset"])
    args = parser.parse_args()

    if args.action == "init":
        run_migrations()
    else:
        reset_database()


if __name__ == "__main__":
    main()
