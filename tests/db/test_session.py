from sqlalchemy import text

from app.db.session import get_engine


def test_get_engine_connects_and_is_cached(postgres_container, monkeypatch):
    database_url = postgres_container.get_connection_url().replace(
        "postgresql+psycopg2://", "postgresql+psycopg://"
    )
    monkeypatch.setenv("INTERNAL_API_KEY", "test-key")
    monkeypatch.setenv("DATABASE_URL", database_url)

    engine_first = get_engine()
    with engine_first.connect() as connection:
        result = connection.execute(text("SELECT 1")).scalar_one()

    assert result == 1
    assert get_engine() is engine_first
