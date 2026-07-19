import logging
from string import Template

from fastapi import HTTPException, status
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domains.ai.suh_aider_client import call_chat
from app.domains.crawling.model import CongestionSnapshot
from app.domains.crawling.service import list_congestion_snapshots
from app.domains.facility.model import Facility
from app.domains.facility.schema import FacilityResponse
from app.domains.facility.service import get_facility_by_code, list_facilities
from app.domains.prompt.model import PromptTemplate
from app.domains.prompt.service import get_active_prompt_template
from app.domains.recommendation.model import PreferenceCategoryMapping, RecommendationHistory
from app.domains.recommendation.route_optimizer import optimize_route
from app.domains.recommendation.schema import (
    CompanionType,
    LlmRecommendationResponse,
    PreferenceCategoryMappingCreate,
    PreferenceTag,
    RecommendationRoutesRequest,
    RecommendationRoutesResponse,
    RecommendedCourse,
    RouteStop,
)
from app.domains.weather.model import WeatherSnapshot
from app.domains.weather.service import get_latest_weather_snapshot

logger = logging.getLogger(__name__)

_MAX_ATTEMPTS = 2  # 최초 시도 + 1회 재시도
_ENTRANCE_CATEGORY = "출입문"
_MAX_DESCRIPTION_LENGTH_IN_PROMPT = (
    200  # 관리자 입력 자유 텍스트가 프롬프트를 과도하게 지배하지 않도록 제한
)

_COMPANION_TYPE_HINTS: dict[CompanionType, str] = {
    "ALONE": "관심사 중심, 이동 효율 우선, 조용한 코스 가능",
    "WITH_CHILD": "짧은 이동, 쉬운 퀴즈, 체험형 장소, 화장실·휴식 공간 고려",
    "WITH_PARTNER": "포토스팟, 산책, 분위기 좋은 장소",
    "WITH_FRIENDS": "액티비티, 넓은 동선, 활동형 장소",
    "WITH_ELDERLY": "짧은 이동, 평지 위주, 휴식 공간 자주 포함",
}


def create_preference_category_mapping(
    db: Session, data: PreferenceCategoryMappingCreate
) -> PreferenceCategoryMapping:
    mapping = PreferenceCategoryMapping(**data.model_dump())
    db.add(mapping)
    db.commit()
    db.refresh(mapping)
    return mapping


def list_preference_category_mappings(
    db: Session, preference_tag: PreferenceTag | None = None
) -> list[PreferenceCategoryMapping]:
    stmt = select(PreferenceCategoryMapping)
    if preference_tag is not None:
        stmt = stmt.where(PreferenceCategoryMapping.preference_tag == preference_tag)
    return list(db.scalars(stmt).all())


def get_preference_category_mapping(
    db: Session, mapping_id: int
) -> PreferenceCategoryMapping | None:
    return db.get(PreferenceCategoryMapping, mapping_id)


def delete_preference_category_mapping(db: Session, mapping: PreferenceCategoryMapping) -> None:
    db.delete(mapping)
    db.commit()


def _select_candidate_facilities(
    db: Session, preference_tags: list[PreferenceTag] | None
) -> list[Facility]:
    stmt = select(PreferenceCategoryMapping.category)
    if preference_tags:
        stmt = stmt.where(PreferenceCategoryMapping.preference_tag.in_(preference_tags))
    target_categories = set(db.scalars(stmt).all())
    # 좌표 없는 시설은 경로 최적화 알고리즘이 다룰 수 없으므로 후보 단계에서 제외한다.
    # 출입문 카테고리가 실수로 매핑되더라도 게이트가 중간 방문지 후보로 섞이지 않도록 제외한다
    # (입구/출구는 이미 별도 필드로 고정되므로, 섞이면 요청마다 입구/출구 누출 검증 실패가
    # 반복될 수 있다).
    return [
        f
        for f in list_facilities(db)
        if f.category in target_categories
        and f.category != _ENTRANCE_CATEGORY
        and f.latitude is not None
        and f.longitude is not None
    ]


def _get_entrance_exit_facilities(
    db: Session, entrance_facility_code: str, exit_facility_code: str
) -> tuple[Facility, Facility]:
    entrance = get_facility_by_code(db, entrance_facility_code)
    if entrance is None or entrance.category != _ENTRANCE_CATEGORY:
        detail = "entrance_facility_code가 유효한 출입구 Facility를 가리키지 않습니다"
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=detail)
    exit_facility = get_facility_by_code(db, exit_facility_code)
    if exit_facility is None or exit_facility.category != _ENTRANCE_CATEGORY:
        detail = "exit_facility_code가 유효한 출입구 Facility를 가리키지 않습니다"
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=detail)
    if entrance.latitude is None or entrance.longitude is None:
        detail = "entrance_facility_code에 해당하는 Facility에 좌표 정보가 없습니다"
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=detail)
    if exit_facility.latitude is None or exit_facility.longitude is None:
        detail = "exit_facility_code에 해당하는 Facility에 좌표 정보가 없습니다"
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=detail)
    return entrance, exit_facility


def _format_facility_candidate(facility: Facility) -> str:
    location = f"({facility.latitude}, {facility.longitude})"
    description = (facility.intro or facility.description or "")[:_MAX_DESCRIPTION_LENGTH_IN_PROMPT]
    return (
        f"- id={facility.id}, name={facility.name}, category={facility.category}, "
        f"위치={location}, 설명={description}"
    )


def _build_prompt_variables(
    candidates: list[Facility],
    entrance: Facility,
    exit_facility: Facility,
    weather: WeatherSnapshot | None,
    congestion: CongestionSnapshot | None,
    data: RecommendationRoutesRequest,
) -> dict[str, str]:
    candidates_text = "\n".join(_format_facility_candidate(f) for f in candidates)
    weather_text = (
        f"기온 {weather.temperature}도, 습도 {weather.humidity}%, "
        f"하늘상태 {weather.sky_condition or '정보없음'}, 강수 {weather.precipitation_type}"
        if weather is not None
        else "날씨 정보 없음"
    )
    congestion_text = (
        f"{congestion.congestion_level} ({congestion.congestion_message})"
        if congestion is not None
        else "혼잡도 정보 없음"
    )
    variables = {
        "candidates": candidates_text,
        "weather": weather_text,
        "congestion": congestion_text,
        "entrance": _format_facility_candidate(entrance),
        "exit": _format_facility_candidate(exit_facility),
    }
    # 사용자가 선택하지 않은 항목은 프롬프트 변수 자체를 생략한다(safe_substitute는 매핑에
    # 없는 자리표시자를 에러 없이 그대로 남기므로, 빈 문자열 등 임의 기본값을 넣지 않는다).
    if data.preference_tags:
        variables["preference_tags"] = ", ".join(data.preference_tags)
    if data.stay_duration_minutes is not None:
        variables["stay_duration_minutes"] = str(data.stay_duration_minutes)
    if data.companion_type is not None:
        variables["companion_type"] = _COMPANION_TYPE_HINTS[data.companion_type]
    return variables


def _strip_markdown_fences(text: str) -> str:
    """LLM이 JSON을 ```json ... ``` 코드 펜스로 감싸 응답하는 경우를 대비해 벗겨낸다."""
    stripped = text.strip()
    if not stripped.startswith("```"):
        return stripped
    lines = stripped.splitlines()
    lines = lines[1:]
    if lines and lines[-1].strip() == "```":
        lines = lines[:-1]
    return "\n".join(lines)


def _require_coordinates(facility: Facility) -> tuple[float, float]:
    """좌표가 보장돼야 하는 지점에서 float | None을 좁혀 mypy strict를 통과시킨다."""
    latitude, longitude = facility.latitude, facility.longitude
    if latitude is None or longitude is None:
        raise RuntimeError(f"좌표 없는 시설이 처리 과정에 포함됨: facility_id={facility.id}")
    return latitude, longitude


def _parse_llm_response(
    content: str,
    valid_facility_ids: set[int],
    entrance: Facility,
    exit_facility: Facility,
    facilities_by_id: dict[int, Facility],
) -> RecommendationRoutesResponse:
    try:
        parsed = LlmRecommendationResponse.model_validate_json(_strip_markdown_fences(content))
    except ValidationError as exc:
        logger.warning("LLM 응답 파싱 실패", exc_info=True)
        raise RuntimeError(f"LLM 응답 파싱 실패: {exc}") from exc

    entrance_point = _require_coordinates(entrance)
    exit_point = _require_coordinates(exit_facility)
    # 응답 조립 시 입구/출구까지 포함해 facility_id로 실제 Facility 객체를 되찾기 위한 맵
    # (facilities_by_id는 중간 방문지 후보만 담고 있어 입구/출구가 빠져있다)
    all_facilities_by_id: dict[int, Facility] = {
        **facilities_by_id,
        entrance.id: entrance,
        exit_facility.id: exit_facility,
    }

    courses: list[RecommendedCourse] = []
    for llm_course in parsed.courses:
        if len(set(llm_course.facility_ids)) != len(llm_course.facility_ids):
            logger.warning(
                "LLM 응답의 코스에 중복된 facility_id가 포함됨: %s", llm_course.facility_ids
            )
            raise RuntimeError(
                f"LLM 응답의 코스에 중복된 facility_id가 포함됨: {llm_course.facility_ids}"
            )
        for facility_id in llm_course.facility_ids:
            if facility_id in (entrance.id, exit_facility.id):
                logger.warning(
                    "LLM 응답에 입구/출구 facility_id가 중간 방문지로 포함됨: %s", facility_id
                )
                raise RuntimeError(
                    f"LLM 응답에 입구/출구 facility_id가 중간 방문지로 포함됨: {facility_id}"
                )
            if facility_id not in valid_facility_ids:
                logger.warning("LLM 응답에 존재하지 않는 facility_id가 포함됨: %s", facility_id)
                raise RuntimeError(f"LLM 응답에 존재하지 않는 facility_id가 포함됨: {facility_id}")

        waypoints = [
            (facility_id, *_require_coordinates(facilities_by_id[facility_id]))
            for facility_id in llm_course.facility_ids
        ]
        ordered_ids = optimize_route(start=entrance_point, end=exit_point, waypoints=waypoints)
        stop_ids = [entrance.id, *ordered_ids, exit_facility.id]
        stops = [
            RouteStop(
                facility=FacilityResponse.model_validate(all_facilities_by_id[facility_id]),
                order=order,
            )
            for order, facility_id in enumerate(stop_ids, start=1)
        ]
        courses.append(
            RecommendedCourse(title=llm_course.title, reason=llm_course.reason, stops=stops)
        )
    return RecommendationRoutesResponse(courses=courses)


def _save_recommendation_history_best_effort(
    db: Session,
    data: RecommendationRoutesRequest,
    *,
    is_success: bool,
    response: RecommendationRoutesResponse | None,
    failure_status_code: int | None,
    failure_reason: str | None,
    prompt_template_id: int | None,
    model: str | None,
) -> None:
    """이력 저장은 부가 기능이므로, 저장 자체가 실패해도 추천 응답에는 영향을 주지 않는다."""
    try:
        history = RecommendationHistory(
            request=data.model_dump(mode="json"),
            is_success=is_success,
            response=response.model_dump(mode="json") if response is not None else None,
            failure_status_code=failure_status_code,
            failure_reason=failure_reason,
            prompt_template_id=prompt_template_id,
            model=model,
        )
        db.add(history)
        db.commit()
    except Exception:
        db.rollback()
        logger.warning("추천 이력 저장 실패", exc_info=True)


def _generate_recommendation_with_prompt(
    db: Session, data: RecommendationRoutesRequest, prompt: PromptTemplate
) -> RecommendationRoutesResponse:
    entrance, exit_facility = _get_entrance_exit_facilities(
        db, data.entrance_facility_code, data.exit_facility_code
    )

    candidates = _select_candidate_facilities(db, data.preference_tags)
    if not candidates:
        detail = "선택한 선호 태그에 해당하는 추천 후보가 없습니다"
        # starlette 최신 버전에서 HTTP_422_UNPROCESSABLE_ENTITY가 deprecated돼 이 이름을 쓴다
        # (값은 동일하게 422, 에러 코드 문자열도 여전히 UNPROCESSABLE_ENTITY로 나온다)
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=detail)

    weather = get_latest_weather_snapshot(db)
    congestion_snapshots = list_congestion_snapshots(db, limit=1)
    congestion = congestion_snapshots[0] if congestion_snapshots else None

    variables = _build_prompt_variables(
        candidates, entrance, exit_facility, weather, congestion, data
    )
    template = Template(prompt.template_text)
    missing_vars = template.get_identifiers() - variables.keys()
    if missing_vars:
        # 활성 템플릿이 최신 변수명(entrance/exit/companion_type 등)으로 갱신되지 않은 경우를
        # 조용히 넘어가지 않고 로그로 남긴다 — safe_substitute는 매핑에 없는 자리표시자를
        # 에러 없이 그대로 남기므로, 이 로그가 없으면 배포 후 무음 실패가 된다.
        logger.warning(
            "프롬프트 템플릿에 이번 요청에서 채워지지 않은 변수가 있음(오래된 플레이스홀더일 "
            "가능성): %s",
            sorted(missing_vars),
        )
    system_content = template.safe_substitute(variables)
    messages = [{"role": "system", "content": system_content}]
    facilities_by_id = {facility.id: facility for facility in candidates}
    valid_facility_ids = set(facilities_by_id.keys())

    last_error = RuntimeError("추천 생성 실패")
    for _ in range(_MAX_ATTEMPTS):
        try:
            content = call_chat(model=prompt.model, messages=messages)
            return _parse_llm_response(
                content, valid_facility_ids, entrance, exit_facility, facilities_by_id
            )
        except RuntimeError as exc:
            last_error = exc
    raise HTTPException(
        status_code=status.HTTP_502_BAD_GATEWAY, detail=str(last_error)
    ) from last_error


def generate_recommendation(
    db: Session, data: RecommendationRoutesRequest
) -> RecommendationRoutesResponse:
    prompt = get_active_prompt_template(db, purpose="recommendation")
    if prompt is None:
        detail = "활성화된 추천 프롬프트가 없습니다"
        _save_recommendation_history_best_effort(
            db,
            data,
            is_success=False,
            response=None,
            failure_status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            failure_reason=detail,
            prompt_template_id=None,
            model=None,
        )
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=detail)

    try:
        result = _generate_recommendation_with_prompt(db, data, prompt)
    except HTTPException as exc:
        _save_recommendation_history_best_effort(
            db,
            data,
            is_success=False,
            response=None,
            failure_status_code=exc.status_code,
            failure_reason=str(exc.detail),
            prompt_template_id=prompt.id,
            model=prompt.model,
        )
        raise

    _save_recommendation_history_best_effort(
        db,
        data,
        is_success=True,
        response=result,
        failure_status_code=None,
        failure_reason=None,
        prompt_template_id=prompt.id,
        model=prompt.model,
    )
    return result
