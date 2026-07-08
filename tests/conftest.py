import os
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from testcontainers.postgres import PostgresContainer

from app.core.config import get_settings
from app.db.session import get_engine


@pytest.fixture(scope="session")
def postgres_container():
    with PostgresContainer(
        "postgres:16-alpine", username="eodaego_ai", password="eodaego_ai", dbname="eodaego_ai"
    ) as container:
        yield container


@pytest.fixture(autouse=True)
def _clear_caches():
    get_settings.cache_clear()
    get_engine.cache_clear()
    yield
    get_settings.cache_clear()
    get_engine.cache_clear()


@pytest.fixture(scope="session")
def db_engine(postgres_container):
    database_url = postgres_container.get_connection_url().replace(
        "postgresql+psycopg2://", "postgresql+psycopg://"
    )
    previous_env = {
        "INTERNAL_API_KEY": os.environ.get("INTERNAL_API_KEY"),
        "DATABASE_URL": os.environ.get("DATABASE_URL"),
    }
    os.environ["INTERNAL_API_KEY"] = "test-key"
    os.environ["DATABASE_URL"] = database_url

    project_root = Path(__file__).resolve().parents[1]
    alembic_cfg = Config(str(project_root / "alembic.ini"))
    alembic_cfg.set_main_option("script_location", str(project_root / "alembic"))
    command.upgrade(alembic_cfg, "head")

    engine = create_engine(database_url)
    yield engine
    engine.dispose()

    for key, value in previous_env.items():
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value


@pytest.fixture
def db_session(db_engine):
    connection = db_engine.connect()
    transaction = connection.begin()
    session_factory = sessionmaker(bind=connection)
    session = session_factory()

    yield session

    session.close()
    transaction.rollback()
    connection.close()
