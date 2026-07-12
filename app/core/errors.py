from http import HTTPStatus
from typing import Literal

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel


class ErrorDetail(BaseModel):
    """공통 에러 응답의 `error` 필드 스키마."""

    code: str
    message: str


class ErrorEnvelope(BaseModel):
    """모든 에러 응답이 따르는 공통 envelope. Swagger `responses=`에서 참조용으로만 쓰인다."""

    success: Literal[False] = False
    data: None = None
    error: ErrorDetail


def _error_response(status_code: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"success": False, "data": None, "error": {"code": code, "message": message}},
    )


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(HTTPException)
    async def handle_http_exception(request: Request, exc: HTTPException) -> JSONResponse:
        code = HTTPStatus(exc.status_code).phrase.upper().replace(" ", "_")
        return _error_response(exc.status_code, code=code, message=str(exc.detail))

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        return _error_response(422, code="VALIDATION_ERROR", message=str(exc.errors()))

    @app.exception_handler(Exception)
    async def handle_unhandled_exception(request: Request, exc: Exception) -> JSONResponse:
        return _error_response(500, code="INTERNAL_SERVER_ERROR", message="unexpected server error")
