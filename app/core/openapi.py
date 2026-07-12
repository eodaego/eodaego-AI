from typing import Any

from app.core.errors import ErrorEnvelope


def error_response(code: str, message: str, description: str) -> dict[str, Any]:
    """단일 상태 코드에 대한 OpenAPI `responses` 항목을 만든다.

    호출부에서 `{404: error_response(...)}`처럼 딕셔너리 키로 실제 상태 코드를 지정하므로,
    이 함수 자체는 상태 코드를 인자로 받지 않는다.

    `core/errors.py`가 실제로 만드는 에러 envelope({success, data, error})과 동일한
    스키마·예시를 Swagger UI에 노출해, BE가 실제 응답 형태를 코드 확인 없이 파악할
    수 있게 한다.
    """
    return {
        "model": ErrorEnvelope,
        "description": description,
        "content": {
            "application/json": {
                "example": {
                    "success": False,
                    "data": None,
                    "error": {"code": code, "message": message},
                }
            }
        },
    }


# FastAPI의 `responses` 파라미터 타입(`dict[int | str, dict[str, Any]] | None`)과 정확히 맞춰야
# mypy --strict가 통과한다. dict는 키 타입에 대해 invariant이므로 `dict[int, ...]`로 선언하면
# `responses=`에 그대로 전달하거나 `{**이 상수, ...}`로 언팩할 때 [arg-type]/[dict-item] 에러가 난다.  # noqa: E501
_UNAUTHORIZED: dict[int | str, dict[str, Any]] = {
    401: error_response(
        "UNAUTHORIZED",
        "invalid internal api key",
        "X-Internal-Api-Key 헤더 값이 설정된 INTERNAL_API_KEY와 일치하지 않음 "
        "(헤더 자체가 없으면 401이 아니라 422가 발생함)",
    )
}

_VALIDATION_ERROR: dict[int | str, dict[str, Any]] = {
    422: error_response(
        "VALIDATION_ERROR",
        "[{'type': 'missing', 'loc': ('body', 'name'), 'msg': 'Field required', "
        "'input': {}, 'url': 'https://errors.pydantic.dev/2.9/v/missing'}]",
        "요청 바디/쿼리/경로 파라미터 또는 필수 헤더(X-Internal-Api-Key)가 스키마 검증에 "
        "실패함 (Pydantic의 에러 목록이 문자열로 직렬화되어 message에 담김 — 실제 항목 "
        "수·필드는 검증 실패 내용에 따라 다름)",
    )
}

_INTERNAL_SERVER_ERROR: dict[int | str, dict[str, Any]] = {
    500: error_response(
        "INTERNAL_SERVER_ERROR",
        "unexpected server error",
        "처리되지 않은 서버 내부 예외 (예: DB 유니크 제약 위반을 별도로 처리하지 않는 "
        "생성 API에서의 중복 값 삽입 등)",
    )
}

COMMON_ERRORS: dict[int | str, dict[str, Any]] = {
    **_UNAUTHORIZED,
    **_VALIDATION_ERROR,
    **_INTERNAL_SERVER_ERROR,
}
"""모든 인증 엔드포인트에 공통으로 적용되는 에러 응답(401/422/500).

`X-Internal-Api-Key`가 모든 엔드포인트의 필수 헤더 파라미터이므로, 요청 바디·쿼리·경로
파라미터가 전혀 없는 엔드포인트도 헤더 누락 시 422가 발생할 수 있다 — 따라서 "바디가 있는
엔드포인트만 422가 가능하다"는 구분은 성립하지 않으며, 모든 엔드포인트에 422를 포함한다."""
