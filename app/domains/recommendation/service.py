import logging
from string import Template
from typing import Literal

from fastapi import HTTPException, status
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domains.ai.llm_router import call_with_fallback
from app.domains.crawling.model import CongestionSnapshot
from app.domains.crawling.service import list_congestion_snapshots
from app.domains.facility.model import Facility
from app.domains.facility.schema import FacilityResponse
from app.domains.facility.service import get_facility_by_code, list_facilities
from app.domains.prompt.model import PromptTemplate
from app.domains.prompt.service import get_active_prompt_template
from app.domains.recommendation.fallback import (
    FallbackCandidate,
    build_fallback_courses,
)
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

_RECOMMENDATION_PROMPT_TRIGGER = (
    "위 지침과 후보 목록을 참고해 지정된 JSON 스키마 형식으로 추천 코스 3개를 생성하라. "
    "각 코스의 estimated_duration_minutes(분 단위 예상 소요시간)는 방문지 수·시설 유형·이동을 "
    "종합적으로 고려해 추정하라. 위 희망 체류 시간과는 독립적인 값이므로 그 값을 그대로 "
    "반복하지 마라."
)
_NOT_SPECIFIED = "지정하지 않음"
_RECOMMENDATION_RESPONSE_SCHEMA = LlmRecommendationResponse.model_json_schema()
_COURSE_LABELS: tuple[Literal["A", "B", "C"], ...] = ("A", "B", "C")
_ENTRANCE_CATEGORY = "출입문"
_ALGORITHM_FALLBACK_MODEL = "algorithm:fallback"
_MAX_DESCRIPTION_LENGTH_IN_PROMPT = (
    60  # SUH-AIder num_ctx(4096) 안에 입력+출력이 들어오도록 후보 한 줄의 길이를 제한
)

_COMPANION_TYPE_HINTS: dict[CompanionType, str] = {
    "ALONE": "관심사 중심, 이동 효율 우선, 조용한 코스 가능",
    "WITH_CHILD": "짧은 이동, 쉬운 퀴즈, 체험형 장소, 화장실·휴식 공간 고려",
    "WITH_PARTNER": "포토스팟, 산책, 분위기 좋은 장소",
    "WITH_FRIENDS": "액티비티, 넓은 동선, 활동형 장소",
    "WITH_ELDERLY": "짧은 이동, 평지 위주, 휴식 공간 자주 포함",
}


class _LlmUnavailableError(Exception):
    """LLM으로 추천을 만들 수 없어 알고리즘 fallback으로 전환해야 함을 알리는 내부 예외."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


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
    # 좌표는 후보 단계에서 None이 걸러져 항상 float이다. 소수점 4자리(약 10m)로 토큰을 아낀다.
    location = f"({facility.latitude:.4f}, {facility.longitude:.4f})"
    description = (facility.intro or facility.description or "")[:_MAX_DESCRIPTION_LENGTH_IN_PROMPT]
    return (
        f"- id={facility.id}, name={facility.name}, category={facility.category}, "
        f"위치={location}, 설명={description}"
    )


def _build_system_variables(
    candidates: list[Facility],
    entrance: Facility,
    exit_facility: Facility,
    weather: WeatherSnapshot | None,
    congestion: CongestionSnapshot | None,
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
    return {
        "candidates": candidates_text,
        "weather": weather_text,
        "congestion": congestion_text,
        "entrance": _format_facility_candidate(entrance),
        "exit": _format_facility_candidate(exit_facility),
    }


def _build_recommendation_prompt(data: RecommendationRoutesRequest) -> str:
    # 후보 목록·날씨 등 안정적인 데이터는 system(템플릿)에 두고, 요청마다 있을 수도 없을 수도
    # 있는 조건은 여기 prompt에 항상 같은 형태(값이 없으면 "지정하지 않음")로 담는다 — system
    # 쪽에 이 조건들을 치환해 넣었을 때 특정 조합에서 SUH-AIder가 빈 응답을 반환하는 현상이
    # 확인되어(이슈 #46), system 템플릿 형태는 항상 동일하게 유지하고 조건은 prompt로 분리했다.
    preference_tags_text = (
        ", ".join(data.preference_tags) if data.preference_tags else _NOT_SPECIFIED
    )
    stay_duration_text = (
        f"{data.stay_duration_minutes}분"
        if data.stay_duration_minutes is not None
        else _NOT_SPECIFIED
    )
    companion_text = (
        _COMPANION_TYPE_HINTS[data.companion_type]
        if data.companion_type is not None
        else _NOT_SPECIFIED
    )
    return (
        "이번 요청의 조건:\n"
        f"- 선호 태그: {preference_tags_text}\n"
        f"- 희망 체류 시간: {stay_duration_text}\n"
        f"- 동반자 유형 고려사항: {companion_text}\n\n"
        f"{_RECOMMENDATION_PROMPT_TRIGGER}"
    )


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


def _build_route_stops(
    ordered_ids: list[int],
    entrance: Facility,
    exit_facility: Facility,
    facilities_by_id: dict[int, Facility],
) -> list[RouteStop]:
    # 응답 조립 시 입구/출구까지 포함해 facility_id로 실제 Facility 객체를 되찾기 위한 맵
    # (facilities_by_id는 중간 방문지 후보만 담고 있어 입구/출구가 빠져있다)
    all_facilities_by_id: dict[int, Facility] = {
        **facilities_by_id,
        entrance.id: entrance,
        exit_facility.id: exit_facility,
    }
    stop_ids = [entrance.id, *ordered_ids, exit_facility.id]
    return [
        RouteStop(
            facility=FacilityResponse.model_validate(all_facilities_by_id[facility_id]),
            order=order,
        )
        for order, facility_id in enumerate(stop_ids, start=1)
    ]


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

    courses: list[RecommendedCourse] = []
    for index, llm_course in enumerate(parsed.courses):
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
        stops = _build_route_stops(ordered_ids, entrance, exit_facility, facilities_by_id)
        courses.append(
            RecommendedCourse(
                label=_COURSE_LABELS[index],
                title=llm_course.title,
                reason=llm_course.reason,
                tag_labels=llm_course.tag_labels,
                estimated_duration_minutes=llm_course.estimated_duration_minutes,
                stops=stops,
            )
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


def _load_course_inputs(
    db: Session, data: RecommendationRoutesRequest
) -> tuple[Facility, Facility, list[Facility]]:
    entrance, exit_facility = _get_entrance_exit_facilities(
        db, data.entrance_facility_code, data.exit_facility_code
    )

    candidates = _select_candidate_facilities(db, data.preference_tags)
    if not candidates:
        detail = "선택한 선호 태그에 해당하는 추천 후보가 없습니다"
        # starlette 최신 버전에서 HTTP_422_UNPROCESSABLE_ENTITY가 deprecated돼 이 이름을 쓴다
        # (값은 동일하게 422, 에러 코드 문자열도 여전히 UNPROCESSABLE_ENTITY로 나온다)
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=detail)
    return entrance, exit_facility, candidates


def _generate_recommendation_with_prompt(
    db: Session,
    data: RecommendationRoutesRequest,
    prompt: PromptTemplate,
    entrance: Facility,
    exit_facility: Facility,
    candidates: list[Facility],
) -> tuple[RecommendationRoutesResponse, str]:
    weather = get_latest_weather_snapshot(db)
    congestion_snapshots = list_congestion_snapshots(db, limit=1)
    congestion = congestion_snapshots[0] if congestion_snapshots else None

    variables = _build_system_variables(candidates, entrance, exit_facility, weather, congestion)
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
    recommendation_prompt = _build_recommendation_prompt(data)
    facilities_by_id = {facility.id: facility for facility in candidates}
    valid_facility_ids = set(facilities_by_id.keys())

    providers = [(p.provider, p.model) for p in prompt.providers if p.is_enabled]
    if not providers:
        raise _LlmUnavailableError("사용 가능한 LLM provider가 없습니다")

    def _parse(content: str) -> RecommendationRoutesResponse:
        return _parse_llm_response(
            content, valid_facility_ids, entrance, exit_facility, facilities_by_id
        )

    try:
        result, used_provider, used_model = call_with_fallback(
            providers=providers,
            system=system_content,
            prompt=recommendation_prompt,
            parse=_parse,
            response_format=_RECOMMENDATION_RESPONSE_SCHEMA,
        )
    except RuntimeError as exc:
        raise _LlmUnavailableError(str(exc)) from exc
    return result, f"{used_provider}:{used_model}"


def _tags_by_category(
    db: Session, preference_tags: list[PreferenceTag] | None
) -> dict[str, frozenset[str]]:
    if not preference_tags:
        return {}
    stmt = select(
        PreferenceCategoryMapping.preference_tag, PreferenceCategoryMapping.category
    ).where(PreferenceCategoryMapping.preference_tag.in_(preference_tags))
    tags: dict[str, set[str]] = {}
    for preference_tag, category in db.execute(stmt).all():
        tags.setdefault(category, set()).add(preference_tag)
    return {category: frozenset(values) for category, values in tags.items()}


def _generate_fallback_recommendation(
    data: RecommendationRoutesRequest,
    entrance: Facility,
    exit_facility: Facility,
    candidates: list[Facility],
    tags_by_category: dict[str, frozenset[str]],
) -> RecommendationRoutesResponse:
    facilities_by_id = {facility.id: facility for facility in candidates}
    fallback_candidates: list[FallbackCandidate] = []
    for facility in candidates:
        latitude, longitude = _require_coordinates(facility)
        fallback_candidates.append(
            FallbackCandidate(
                facility_id=facility.id,
                category=facility.category,
                latitude=latitude,
                longitude=longitude,
                tags=tags_by_category.get(facility.category, frozenset()),
            )
        )
    fallback_courses = build_fallback_courses(
        _require_coordinates(entrance),
        _require_coordinates(exit_facility),
        fallback_candidates,
        data.stay_duration_minutes,
    )
    courses = [
        RecommendedCourse(
            label=label,
            title=course.title,
            reason=course.reason,
            tag_labels=list(course.tag_labels),
            estimated_duration_minutes=course.estimated_duration_minutes,
            stops=_build_route_stops(
                list(course.ordered_facility_ids), entrance, exit_facility, facilities_by_id
            ),
        )
        for label, course in zip(_COURSE_LABELS, fallback_courses, strict=True)
    ]
    return RecommendationRoutesResponse(courses=courses)


def generate_recommendation(
    db: Session, data: RecommendationRoutesRequest
) -> RecommendationRoutesResponse:
    prompt = get_active_prompt_template(db, purpose="recommendation")
    try:
        entrance, exit_facility, candidates = _load_course_inputs(db, data)
    except HTTPException as exc:
        _save_recommendation_history_best_effort(
            db,
            data,
            is_success=False,
            response=None,
            failure_status_code=exc.status_code,
            failure_reason=str(exc.detail),
            prompt_template_id=prompt.id if prompt else None,
            model=None,
        )
        raise

    unavailable_reason = "활성화된 추천 프롬프트가 없습니다"
    if prompt is not None:
        try:
            result, used_model = _generate_recommendation_with_prompt(
                db, data, prompt, entrance, exit_facility, candidates
            )
        except _LlmUnavailableError as exc:
            unavailable_reason = exc.reason
        else:
            _save_recommendation_history_best_effort(
                db,
                data,
                is_success=True,
                response=result,
                failure_status_code=None,
                failure_reason=None,
                prompt_template_id=prompt.id,
                model=used_model,
            )
            return result

    logger.warning("LLM 추천 불가로 알고리즘 fallback 전환: %s", unavailable_reason)
    fallback_result = _generate_fallback_recommendation(
        data,
        entrance,
        exit_facility,
        candidates,
        _tags_by_category(db, data.preference_tags),
    )
    _save_recommendation_history_best_effort(
        db,
        data,
        is_success=True,
        response=fallback_result,
        failure_status_code=None,
        failure_reason=unavailable_reason,
        prompt_template_id=None,
        model=_ALGORITHM_FALLBACK_MODEL,
    )
    return fallback_result
