from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.openapi import COMMON_ERRORS, error_response
from app.core.security import verify_internal_api_key
from app.db.session import get_db
from app.domains.recommendation import service
from app.domains.recommendation.schema import (
    PreferenceCategoryMappingCreate,
    PreferenceCategoryMappingResponse,
    PreferenceTag,
    RecommendationRoutesRequest,
    RecommendationRoutesResponse,
)

router = APIRouter(
    prefix="/api/v1/recommendation",
    tags=["recommendation"],
    dependencies=[Depends(verify_internal_api_key)],
)

_MAPPING_NOT_FOUND_RESPONSE = error_response(
    "NOT_FOUND",
    "preference category mapping not found",
    "path의 mapping_id에 해당하는 매핑이 없음",
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
            "Facility 후보가 0건이거나(GET /api/v1/recommendation/preference-mappings로 조회 "
            "가능한 매핑이 하나도 없는 태그만 선택했거나, 매핑된 시설 전부에 좌표 정보가 없는 "
            '경우 포함), entrance_facility_code/exit_facility_code가 category="출입문"인 '
            "Facility.code와 일치하지 않거나 해당 Facility에 좌표 정보가 없어 처리 불가능한 "
            "경우다",
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
    """사용자 입력(선호 태그·체류 시간·입구/출구·동반자 유형)만 받아, AI가 자체 보유한
    Facility(시설 위치)·날씨·혼잡도 데이터를 조합해 추천 동선을 생성한다. 입구/출구를 제외한
    선호 태그·체류 시간·동반자 유형은 선택 사항이다(생략 시 해당 조건 없이 추천).

    **처리 순서**
    1. `purpose='recommendation'`이고 `is_active=true`인 프롬프트 템플릿을 조회한다. 없으면 503.
    2. `entrance_facility_code`/`exit_facility_code`가 `category="출입문"`인 `Facility.code`와
       일치하고 좌표 정보를 가지고 있는지 검증한다. 아니면 422.
    3. `preference_tags`에 매핑된 카테고리의 `Facility` 후보를 조회한다(좌표가 없는 시설은
       후보에서 제외된다). 선택하지 않았거나 빈 배열이면 매핑된 모든 카테고리를 대상으로
       조회한다. 0건이면 422.
    4. 최신 날씨 스냅샷과 공원 전체 혼잡도를 조회한다.
    5. 프롬프트 템플릿에 후보·입구·출구·날씨·혼잡도·사용자 입력을 치환해 SUH-AIder를 호출한다
       (선택하지 않은 항목은 치환 변수에서 생략된다). LLM은 각 코스마다 입구/출구를 제외한
       중간 방문지 facility_id만 결정한다.
    6. 응답을 파싱/검증한다(존재하지 않거나 입구/출구인 facility_id를 중간 방문지로 잘못
       포함시켰거나, 한 코스 안에서 facility_id가 중복된 경우 실패로 간주). 실제 방문 순서는
       LLM이 아니라, 입구/출구 좌표를 고정하고 중간 방문지 간 직선거리 합을 최소화하는 서버
       알고리즘(최근접 이웃+2-opt)이 계산한다.
    7. 5~6단계가 실패하면 1회 재시도하고, 그래도 실패하면 502.
    """
    return service.generate_recommendation(db, data)


@router.post(
    "/preference-mappings",
    response_model=PreferenceCategoryMappingResponse,
    status_code=status.HTTP_201_CREATED,
    summary="취향 태그-시설 카테고리 매핑 생성 (관리자)",
    responses={
        **COMMON_ERRORS,
        409: error_response(
            "CONFLICT",
            "preference category mapping already exists",
            "동일한 (preference_tag, category) 조합이 이미 존재함",
        ),
    },
)
def create_preference_mapping(
    data: PreferenceCategoryMappingCreate, db: Session = Depends(get_db)
) -> PreferenceCategoryMappingResponse:
    """관리자가 취향 태그-시설 카테고리 매핑을 등록한다. 동일한 (preference_tag, category)
    조합이 이미 존재하면 409를 반환한다.
    """
    try:
        mapping = service.create_preference_category_mapping(db, data)
    except IntegrityError:
        db.rollback()
        detail = "preference category mapping already exists"
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail) from None
    return PreferenceCategoryMappingResponse.model_validate(mapping)


@router.get(
    "/preference-mappings",
    response_model=list[PreferenceCategoryMappingResponse],
    summary="취향 태그-시설 카테고리 매핑 전체 목록 조회",
    responses=COMMON_ERRORS,
)
def list_preference_mappings(
    preference_tag: Annotated[
        PreferenceTag | None, Query(description="지정 시 해당 취향 태그의 매핑만 필터링.")
    ] = None,
    db: Session = Depends(get_db),
) -> list[PreferenceCategoryMappingResponse]:
    """정렬 조건 없이 전체 매핑을 반환한다. `preference_tag` 쿼리 파라미터를 지정하면
    해당 태그의 매핑만 필터링한다.
    """
    mappings = service.list_preference_category_mappings(db, preference_tag=preference_tag)
    return [PreferenceCategoryMappingResponse.model_validate(m) for m in mappings]


@router.delete(
    "/preference-mappings/{mapping_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="취향 태그-시설 카테고리 매핑 삭제",
    responses={**COMMON_ERRORS, 404: _MAPPING_NOT_FOUND_RESPONSE},
)
def delete_preference_mapping(mapping_id: int, db: Session = Depends(get_db)) -> None:
    """대상이 없으면 404."""
    mapping = service.get_preference_category_mapping(db, mapping_id)
    if mapping is None:
        detail = "preference category mapping not found"
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)
    service.delete_preference_category_mapping(db, mapping)
