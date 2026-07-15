import logging
from string import Template

from fastapi import HTTPException, status
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.domains.ai.suh_aider_client import call_chat
from app.domains.crawling.model import CongestionSnapshot
from app.domains.crawling.service import list_congestion_snapshots
from app.domains.facility.model import Facility
from app.domains.facility.service import get_facility, list_facilities
from app.domains.prompt.service import get_active_prompt_template
from app.domains.recommendation.schema import (
    CompanionType,
    PreferenceTag,
    RecommendationRoutesRequest,
    RecommendationRoutesResponse,
)
from app.domains.weather.model import WeatherSnapshot
from app.domains.weather.service import get_latest_weather_snapshot

logger = logging.getLogger(__name__)

_MAX_ATTEMPTS = 2  # 최초 시도 + 1회 재시도
_ENTRANCE_CATEGORY = "출입문"

_PREFERENCE_TAG_CATEGORIES: dict[PreferenceTag, tuple[str, ...]] = {
    "ANIMAL": ("동물나라",),
    "NATURE": ("자연나라", "조경시설"),
    "ACTIVITY": ("재미나라", "체험시설", "운동 및 대관시설"),
    "RELAXATION": ("조경시설",),
}
# PHOTO_SPOT/CULTURE_EVENT/LEARNING은 매핑되는 Facility.category가 아직 없어 dict에 없음
# (선택 시 후보 0건 → 422. 관리자 편집 기능은 별도 이슈로 분리됨)

_COMPANION_TYPE_HINTS: dict[CompanionType, str] = {
    "ALONE": "관심사 중심, 이동 효율 우선, 조용한 코스 가능",
    "WITH_CHILD": "짧은 이동, 쉬운 퀴즈, 체험형 장소, 화장실·휴식 공간 고려",
    "WITH_PARTNER": "포토스팟, 산책, 분위기 좋은 장소",
    "WITH_FRIENDS": "액티비티, 넓은 동선, 활동형 장소",
    "WITH_ELDERLY": "짧은 이동, 평지 위주, 휴식 공간 자주 포함",
}


def _select_candidate_facilities(
    db: Session, preference_tags: list[PreferenceTag]
) -> list[Facility]:
    target_categories = {
        category for tag in preference_tags for category in _PREFERENCE_TAG_CATEGORIES.get(tag, ())
    }
    return [f for f in list_facilities(db) if f.category in target_categories]


def _get_entrance_exit_facilities(
    db: Session, entrance_facility_id: int, exit_facility_id: int
) -> tuple[Facility, Facility]:
    entrance = get_facility(db, entrance_facility_id)
    if entrance is None or entrance.category != _ENTRANCE_CATEGORY:
        detail = "entrance_facility_id가 유효한 출입구 Facility를 가리키지 않습니다"
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=detail)
    exit_facility = get_facility(db, exit_facility_id)
    if exit_facility is None or exit_facility.category != _ENTRANCE_CATEGORY:
        detail = "exit_facility_id가 유효한 출입구 Facility를 가리키지 않습니다"
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=detail)
    return entrance, exit_facility


def _format_facility_candidate(facility: Facility) -> str:
    location = (
        f"({facility.latitude}, {facility.longitude})"
        if facility.latitude is not None and facility.longitude is not None
        else "위치 정보 없음"
    )
    description = facility.intro or facility.description or ""
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
    return {
        "candidates": candidates_text,
        "weather": weather_text,
        "congestion": congestion_text,
        "preference_tags": ", ".join(data.preference_tags),
        "stay_duration_minutes": str(data.stay_duration_minutes),
        "entrance": _format_facility_candidate(entrance),
        "exit": _format_facility_candidate(exit_facility),
        "companion_type": _COMPANION_TYPE_HINTS[data.companion_type],
    }


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


def _parse_llm_response(content: str, valid_facility_ids: set[int]) -> RecommendationRoutesResponse:
    try:
        parsed = RecommendationRoutesResponse.model_validate_json(_strip_markdown_fences(content))
    except ValidationError as exc:
        logger.warning("LLM 응답 파싱 실패", exc_info=True)
        raise RuntimeError(f"LLM 응답 파싱 실패: {exc}") from exc
    for course in parsed.courses:
        for stop in course.stops:
            if stop.facility_id not in valid_facility_ids:
                logger.warning(
                    "LLM 응답에 존재하지 않는 facility_id가 포함됨: %s", stop.facility_id
                )
                raise RuntimeError(
                    f"LLM 응답에 존재하지 않는 facility_id가 포함됨: {stop.facility_id}"
                )
    return parsed


def generate_recommendation(
    db: Session, data: RecommendationRoutesRequest
) -> RecommendationRoutesResponse:
    prompt = get_active_prompt_template(db, purpose="recommendation")
    if prompt is None:
        detail = "활성화된 추천 프롬프트가 없습니다"
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=detail)

    entrance, exit_facility = _get_entrance_exit_facilities(
        db, data.entrance_facility_id, data.exit_facility_id
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
    system_content = Template(prompt.template_text).safe_substitute(variables)
    messages = [{"role": "system", "content": system_content}]
    valid_facility_ids = {facility.id for facility in candidates} | {
        entrance.id,
        exit_facility.id,
    }

    last_error = RuntimeError("추천 생성 실패")
    for _ in range(_MAX_ATTEMPTS):
        try:
            content = call_chat(model=prompt.model, messages=messages)
            return _parse_llm_response(content, valid_facility_ids)
        except RuntimeError as exc:
            last_error = exc
    raise HTTPException(
        status_code=status.HTTP_502_BAD_GATEWAY, detail=str(last_error)
    ) from last_error
