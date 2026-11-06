import os

# Must be set before the app is imported: disables automatic migrations in the lifespan
os.environ["ENVIRONMENT"] = "test"

from collections.abc import Generator  # noqa: E402

import pytest  # noqa: E402
from alembic import command  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import Engine, create_engine  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402
from testcontainers.community.postgres import PostgresContainer  # noqa: E402

from app.database import get_db  # noqa: E402
from app.db import get_alembic_config  # noqa: E402
from main import app  # noqa: E402

POSTGRES_IMAGE = "postgres:17-alpine"


@pytest.fixture(scope="session")
def database_url() -> Generator[str]:
    """PostgreSQL URL for the test session.

    Uses TEST_DATABASE_URL when provided, otherwise starts a throwaway container (Docker required).
    """
    url = os.environ.get("TEST_DATABASE_URL")
    if url:
        yield url
        return

    with PostgresContainer(
        POSTGRES_IMAGE,
        username="test",
        password="test",
        dbname="test",
        driver="psycopg",
    ) as postgres:
        yield postgres.get_connection_url()


@pytest.fixture(scope="session")
def engine(database_url: str) -> Generator[Engine]:
    """Engine bound to a database whose schema is built by the Alembic migrations."""
    config = get_alembic_config(database_url)
    config.attributes["configure_logger"] = False
    command.upgrade(config, "head")

    test_engine = create_engine(database_url)
    yield test_engine
    test_engine.dispose()


@pytest.fixture
def db_session(engine: Engine) -> Generator[Session]:
    """Session wrapped in an outer transaction rolled back after each test.

    Application commits only release a SAVEPOINT, so nothing leaks between tests.
    """
    connection = engine.connect()
    transaction = connection.begin()
    session = Session(
        bind=connection,
        autoflush=False,
        join_transaction_mode="create_savepoint",
    )
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture(autouse=True)
def override_get_db(db_session: Session) -> Generator[None]:
    """Route every request of every test to the transactional test session."""

    def _get_test_db() -> Generator[Session]:
        yield db_session

    app.dependency_overrides[get_db] = _get_test_db
    yield
    app.dependency_overrides.pop(get_db, None)


@pytest.fixture
def client(override_get_db: None) -> Generator[TestClient]:
    """TestClient whose get_db dependency points to the isolated PostgreSQL session."""
    with TestClient(app) as test_client:
        yield test_client
