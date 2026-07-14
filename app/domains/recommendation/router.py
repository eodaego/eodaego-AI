from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.openapi import COMMON_ERRORS, error_response
from app.core.security import verify_internal_api_key
from app.db.session import get_db
from app.domains.recommendation import service
from app.domains.recommendation.schema import (
    RecommendationRoutesRequest,
    RecommendationRoutesResponse,
)

router = APIRouter(
    prefix="/api/v1/recommendation",
    tags=["recommendation"],
    dependencies=[Depends(verify_internal_api_key)],
)


@router.post(
    "/routes",
    response_model=RecommendationRoutesResponse,
    summary="사용자 맞춤형 추천 동선 생성",
    responses={
        **COMMON_ERRORS,
        422: error_response(
            "UNPROCESSABLE_ENTITY",
            "선택한 선호 태그에 해당하는 추천 후보가 없습니다",
            "요청 스키마 자체가 잘못됐을 때(COMMON_ERRORS의 VALIDATION_ERROR)도 이 상태 코드가 "
            "나올 수 있다. 이 문서 예시는 스키마는 유효하지만 preference_tags에 매핑되는 "
            "Facility 후보가 0건이라 처리 불가능한 경우다",
        ),
        503: error_response(
            "SERVICE_UNAVAILABLE",
            "활성화된 추천 프롬프트가 없습니다",
            "purpose='recommendation'이고 is_active=true인 프롬프트 템플릿이 하나도 없음 — "
            "POST 또는 PATCH /api/v1/prompts로 먼저 활성 템플릿을 만들어야 함",
        ),
        502: error_response(
            "BAD_GATEWAY",
            "SUH-AIder /api/chat 호출 실패 (status=500)",
            "SUH-AIder 호출이 실패했거나 응답을 기대한 구조(courses)로 파싱할 수 없음 "
            "(1회 내부 재시도 후에도 실패)",
        ),
    },
)
def create_route_recommendation(
    data: RecommendationRoutesRequest, db: Session = Depends(get_db)
) -> RecommendationRoutesResponse:
    """사용자 입력(선호 태그·체류 시간·시작 위치·동반 아동 여부)만 받아, AI가 자체 보유한
    Facility(시설 위치)·날씨·혼잡도 데이터를 조합해 추천 동선을 생성한다.

    **처리 순서**
    1. `purpose='recommendation'`이고 `is_active=true`인 프롬프트 템플릿을 조회한다. 없으면 503.
    2. `preference_tags`에 매핑된 카테고리의 `Facility` 후보를 조회한다. 0건이면 422.
    3. 최신 날씨 스냅샷과 공원 전체 혼잡도를 조회한다.
    4. 프롬프트 템플릿에 후보·날씨·혼잡도·사용자 입력을 치환해 SUH-AIder를 호출한다.
    5. 응답을 구조화된 코스 목록으로 파싱/검증한다(존재하지 않는 facility_id 참조 시 실패로 간주).
    6. 4~5단계가 실패하면 1회 재시도하고, 그래도 실패하면 502.
    """
    return service.generate_recommendation(db, data)
