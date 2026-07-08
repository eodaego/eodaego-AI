import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_settings_loads_required_fields_from_env_file(tmp_path, monkeypatch):
    monkeypatch.delenv("INTERNAL_API_KEY", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    env_file = tmp_path / ".env.test"
    env_file.write_text(
        "INTERNAL_API_KEY=test-key\n"
        "DATABASE_URL=postgresql+psycopg://user:pass@localhost:5432/eodaego_ai\n"
    )

    settings = Settings(_env_file=str(env_file))

    assert settings.internal_api_key == "test-key"
    assert settings.database_url == "postgresql+psycopg://user:pass@localhost:5432/eodaego_ai"
    assert settings.app_env == "local"


def test_settings_raises_when_required_field_missing(tmp_path, monkeypatch):
    monkeypatch.delenv("INTERNAL_API_KEY", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    env_file = tmp_path / ".env.empty"
    env_file.write_text("")

    with pytest.raises(ValidationError):
        Settings(_env_file=str(env_file))
