import os

# Must be set before the app is imported: disables automatic migrations in the lifespan
os.environ["ENVIRONMENT"] = "test"

import shutil  # noqa: E402
import sqlite3  # noqa: E402
import subprocess  # noqa: E402
from collections.abc import Generator  # noqa: E402
from datetime import UTC, datetime  # noqa: E402
from typing import Any  # noqa: E402

import pytest  # noqa: E402
from alembic import command  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import Connection, Engine, create_engine, event  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402
from testcontainers.community.postgres import PostgresContainer  # noqa: E402

from app.database import get_db  # noqa: E402
from app.db import get_alembic_config  # noqa: E402
from main import app  # noqa: E402

POSTGRES_IMAGE = "postgres:17-alpine"


def _is_docker_available() -> bool:
    """Return True only if the docker CLI and daemon are reachable."""
    if shutil.which("docker") is None:
        return False
    try:
        res = subprocess.run(
            ["docker", "info"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=3,
            check=False,
        )
        return res.returncode == 0
    except Exception:
        return False


@event.listens_for(Engine, "connect")
def _configure_sqlite_connection(dbapi_connection: Any, _connection_record: Any) -> None:
    """Enable foreign keys, savepoints, and now() on SQLite fallback connections."""
    if isinstance(dbapi_connection, sqlite3.Connection):
        dbapi_connection.isolation_level = None
        dbapi_connection.create_function("now", 0, lambda: datetime.now(UTC).isoformat())
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


@event.listens_for(Engine, "begin")
def _do_sqlite_begin(conn: Connection) -> None:
    """Emit explicit BEGIN so outer transactions and savepoints roll back cleanly on SQLite."""
    if conn.dialect.name == "sqlite":
        raw_conn = conn.connection.dbapi_connection
        if isinstance(raw_conn, sqlite3.Connection) and not raw_conn.in_transaction:
            conn.exec_driver_sql("BEGIN")


@pytest.fixture(scope="session")
def database_url() -> Generator[str]:
    """Database URL for the test session.

    Uses TEST_DATABASE_URL when provided, otherwise starts a throwaway PostgreSQL
    container when Docker is available, falling back to an in-memory SQLite database
    when Docker is not installed.
    """
    url = os.environ.get("TEST_DATABASE_URL")
    if url:
        yield url
        return

    if _is_docker_available():
        with PostgresContainer(
            POSTGRES_IMAGE,
            username="test",
            password="test",
            dbname="test",
            driver="psycopg",
        ) as postgres:
            yield postgres.get_connection_url()
            return

    yield "sqlite://"


@pytest.fixture(scope="session")
def engine(database_url: str) -> Generator[Engine]:
    """Engine bound to a database whose schema is built by the Alembic migrations."""
    config = get_alembic_config(database_url)
    config.attributes["configure_logger"] = False

    if database_url.startswith("sqlite"):
        test_engine = create_engine(
            database_url,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        with test_engine.connect() as connection:
            config.attributes["connection"] = connection
            command.upgrade(config, "head")
            connection.commit()
    else:
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
