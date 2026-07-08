import pytest
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
