import os
from collections.abc import Iterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic_ai import models
from pydantic_ai.models.test import TestModel
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from schema_extractor.agents.schema_agent import build_schema_agent
from schema_extractor.api.deps import get_schema_agent
from schema_extractor.api.main import create_app
from schema_extractor.db import repositories
from schema_extractor.db.session import get_db
from schema_extractor.security import create_access_token

os.environ.setdefault("SECRET_KEY", "test-secret-key-for-tests-only-0123456789")

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


@pytest.fixture()
def app(db) -> FastAPI:
    application = create_app()
    application.dependency_overrides[get_db] = lambda: db
    return application


@pytest.fixture()
def client(app) -> TestClient:
    return TestClient(app)


@pytest.fixture()
def use_agent(app):
    def _use(output: dict) -> None:
        agent = build_schema_agent(TestModel(custom_output_args=output))
        app.dependency_overrides[get_schema_agent] = lambda: agent

    return _use


def _headers_for(db, email: str) -> dict[str, str]:
    user = repositories.create_user(db, email=email, hashed_password="not-used")
    return {"Authorization": f"Bearer {create_access_token(user.id)}"}


@pytest.fixture()
def auth_headers(db):
    return _headers_for(db, "a@example.com")


@pytest.fixture()
def other_headers(db):
    return _headers_for(db, "b@example.com")
