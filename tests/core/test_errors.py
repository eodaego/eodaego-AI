from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from pydantic import BaseModel

from app.core.errors import register_exception_handlers


class _Payload(BaseModel):
    name: str


def _build_test_app() -> FastAPI:
    app = FastAPI()
    register_exception_handlers(app)

    @app.get("/not-found")
    def raise_not_found() -> None:
        raise HTTPException(status_code=404, detail="resource missing")

    @app.get("/boom")
    def raise_unexpected() -> None:
        raise ValueError("boom")

    @app.post("/validate")
    def validate_payload(payload: _Payload) -> dict[str, str]:
        return {"name": payload.name}

    return app


def test_http_exception_returns_error_envelope():
    client = TestClient(_build_test_app())

    response = client.get("/not-found")

    assert response.status_code == 404
    assert response.json() == {
        "success": False,
        "data": None,
        "error": {"code": "NOT_FOUND", "message": "resource missing"},
    }


def test_unhandled_exception_returns_500_envelope():
    client = TestClient(_build_test_app(), raise_server_exceptions=False)

    response = client.get("/boom")

    assert response.status_code == 500
    assert response.json() == {
        "success": False,
        "data": None,
        "error": {"code": "INTERNAL_SERVER_ERROR", "message": "unexpected server error"},
    }


def test_validation_error_returns_error_envelope():
    client = TestClient(_build_test_app())

    response = client.post("/validate", json={})

    assert response.status_code == 422
    body = response.json()
    assert body["success"] is False
    assert body["data"] is None
    assert body["error"]["code"] == "VALIDATION_ERROR"
