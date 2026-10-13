from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import Engine, inspect

from app.database import Base
from app.db import get_alembic_config

EXPECTED_TABLES = {
    "alembic_version",
    "associations",
    "refresh_tokens",
    "roles",
    "tournaments",
    "user_roles",
    "users",
}


def test_migrations_create_expected_tables(engine: Engine):
    assert EXPECTED_TABLES <= set(inspect(engine).get_table_names())


def test_database_is_at_latest_revision(engine: Engine):
    head = ScriptDirectory.from_config(get_alembic_config()).get_current_head()
    with engine.connect() as connection:
        current = MigrationContext.configure(connection).get_current_revision()
    assert current == head


def test_models_match_migrations(engine: Engine):
    with engine.connect() as connection:
        context = MigrationContext.configure(connection, opts={"compare_type": True})
        diff = compare_metadata(context, Base.metadata)
    assert diff == []
