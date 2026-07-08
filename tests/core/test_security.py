import pytest
from fastapi import HTTPException

from app.core.security import verify_internal_api_key


def test_verify_internal_api_key_passes_with_correct_key(monkeypatch):
    monkeypatch.setenv("INTERNAL_API_KEY", "correct-key")
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://user:pass@localhost:5432/eodaego_ai")

    verify_internal_api_key(x_internal_api_key="correct-key")


def test_verify_internal_api_key_raises_with_wrong_key(monkeypatch):
    monkeypatch.setenv("INTERNAL_API_KEY", "correct-key")
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://user:pass@localhost:5432/eodaego_ai")

    with pytest.raises(HTTPException) as exc_info:
        verify_internal_api_key(x_internal_api_key="wrong-key")

    assert exc_info.value.status_code == 401
