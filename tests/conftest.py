import os
from collections.abc import Iterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from pydantic_ai import models
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

os.environ.setdefault("SECRET_KEY", "test-secret")

ROOT = Path(__file__).resolve().parents[1]
TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL", "postgresql+psycopg://app:app@localhost:5433/app_test"
)


def alembic_config() -> Config:
    cfg = Config(str(ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(ROOT / "migrations"))
    cfg.set_main_option("sqlalchemy.url", TEST_DATABASE_URL)
    return cfg


@pytest.fixture(scope="session")
def engine():
    engine = create_engine(TEST_DATABASE_URL)

    if not (engine.url.database or "").endswith("_test"):
        pytest.fail(
            "Test database name must end with '_test' to prevent accidental data loss.",
            pytrace=False,
        )

    try:
        with engine.connect():
            pass
    except OperationalError:
        pytest.fail(
            f"Cannot connect to test database at {TEST_DATABASE_URL}. "
            "Make sure the database exists and is running.",
            pytrace=False,
        )

    with engine.begin() as conn:
        conn.execute(text("DROP SCHEMA public CASCADE"))
        conn.execute(text("CREATE SCHEMA public"))
    command.upgrade(alembic_config(), "head")

    yield engine
    engine.dispose()


@pytest.fixture()
def db(engine) -> Iterator[Session]:
    """Sesja w transakcji, którą wycofujemy po teście: testy nie wpływają na siebie."""
    connection = engine.connect()
    transaction = connection.begin()
    session = Session(
        bind=connection,
        join_transaction_mode="create_savepoint",
        expire_on_commit=False,
    )
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture(autouse=True)
def block_model_requests(monkeypatch):
    monkeypatch.setattr(models, "ALLOW_MODEL_REQUESTS", False)
