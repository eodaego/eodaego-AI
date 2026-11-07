import base64
import logging
import time
from string import Template
from typing import assert_never

from fastapi import HTTPException, status
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.llm_types import ImageInput, LlmProvider
from app.domains.ai.llm_router import call_with_fallback
from app.domains.catalog.model import Animal, Plant
from app.domains.catalog.service import list_animals, list_plants
from app.domains.facility.model import Facility
from app.domains.prompt.service import get_active_prompt_template
from app.domains.recognition.default_prompt import (
    CATALOG_TYPE_LABELS,
    DEFAULT_PHOTO_RECOGNITION_PROMPT,
    DEFAULT_PHOTO_RECOGNITION_PROVIDER,
    PHOTO_RECOGNITION_USER_MESSAGE,
)
from app.domains.recognition.schema import (
    CatalogType,
    LlmPhotoRecognitionResponse,
    PhotoRecognitionResponse,
)

logger = logging.getLogger(__name__)

_PLACE_FACILITY_TYPES = ("문화", "음식", "카페")
_MAX_DESCRIPTION_LENGTH_IN_PROMPT = (
    200  # 도감 데이터의 자유 텍스트 설명이 프롬프트를 과도하게 지배하지 않도록 제한
)
_PLANT_DESCRIPTION_LENGTH_IN_PROMPT = 60
_PHOTO_RECOGNITION_RESPONSE_SCHEMA = LlmPhotoRecognitionResponse.model_json_schema()


def _format_animal_candidate(animal: Animal) -> str:
    return (
        f"- id={animal.id}, name={animal.name}, "
        f"scientific_name={animal.scientific_name or '정보없음'}, "
        f"english_name={animal.english_name or '정보없음'}"
    )


def _format_plant_candidate(plant: Plant) -> str:
    description = (plant.description or "정보없음")[:_PLANT_DESCRIPTION_LENGTH_IN_PROMPT]
    return f"- id={plant.id}, name={plant.name}, description={description}"


def _format_place_candidate(facility: Facility) -> str:
    description = (facility.intro or facility.description or "정보없음")[
        :_MAX_DESCRIPTION_LENGTH_IN_PROMPT
    ]
    return (
        f"- id={facility.id}, name={facility.name}, category={facility.category}, "
        f"description={description}"
    )


def _build_candidates(db: Session, catalog_type: CatalogType) -> tuple[dict[int, str], str]:
    """catalog_type에 해당하는 후보 목록을 (id->name 맵, 프롬프트용 텍스트)로 만든다."""
    if catalog_type == "ANIMAL":
        animals = list_animals(db)
        candidates_by_id = {a.id: a.name for a in animals}
        candidates_text = "\n".join(_format_animal_candidate(a) for a in animals)
        return candidates_by_id, candidates_text
    if catalog_type == "PLANT":
        plants = list_plants(db)
        candidates_by_id = {p.id: p.name for p in plants}
        candidates_text = "\n".join(_format_plant_candidate(p) for p in plants)
        return candidates_by_id, candidates_text
    if catalog_type == "PLACE":
        stmt = select(Facility).where(Facility.facility_type.in_(_PLACE_FACILITY_TYPES))
        facilities = list(db.scalars(stmt).all())
        candidates_by_id = {f.id: f.name for f in facilities}
        candidates_text = "\n".join(_format_place_candidate(f) for f in facilities)
        return candidates_by_id, candidates_text
    assert_never(catalog_type)


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


def _resolve_prompt_and_providers(db: Session) -> tuple[str, list[tuple[LlmProvider, str]]]:
    """활성 템플릿/provider 설정을 해석한다. 설정이 없으면 코드 기본값으로 동작한다."""
    prompt = get_active_prompt_template(db, purpose="photo_recognition")
    if prompt is None:
        return DEFAULT_PHOTO_RECOGNITION_PROMPT, [DEFAULT_PHOTO_RECOGNITION_PROVIDER]
    if not prompt.providers:
        return prompt.template_text, [DEFAULT_PHOTO_RECOGNITION_PROVIDER]
    providers = [(p.provider, p.model) for p in prompt.providers if p.is_enabled]
    if not providers:
        detail = "사용 가능한 LLM provider가 없습니다"
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=detail)
    return prompt.template_text, providers


def _judge_match(
    parsed: LlmPhotoRecognitionResponse, candidates_by_id: dict[int, str]
) -> int | None:
    """matched이고 확신도가 low가 아니며 후보에 존재하는 id일 때만 인정한다."""
    if not parsed.matched:
        return None
    if parsed.confidence == "low":
        logger.warning(
            "LLM이 matched=true이나 confidence=low여서 불일치로 처리: %s", parsed.catalog_id
        )
        return None
    if parsed.catalog_id not in candidates_by_id:
        logger.warning("LLM 응답에 존재하지 않는 catalog_id가 포함됨: %s", parsed.catalog_id)
        return None
    return parsed.catalog_id


def _render_system_prompt(
    template_text: str, candidates_text: str, catalog_type: CatalogType
) -> str:
    variables = {
        "candidates": candidates_text,
        "catalog_type_label": CATALOG_TYPE_LABELS[catalog_type],
    }
    template = Template(template_text)
    missing_vars = template.get_identifiers() - variables.keys()
    if missing_vars:
        logger.warning(
            "사진 인식 프롬프트 템플릿에 채워지지 않은 변수가 있음(오래된 플레이스홀더일 "
            "가능성): %s",
            sorted(missing_vars),
        )
    unused_vars = variables.keys() - template.get_identifiers()
    if "candidates" in unused_vars:
        logger.warning(
            "사진 인식 프롬프트 템플릿에 $candidates 플레이스홀더가 없음(후보가 프롬프트에 "
            "전달되지 않아 항상 matched=false가 됨)"
        )
    if "catalog_type_label" in unused_vars:
        logger.warning("사진 인식 프롬프트 템플릿에 $catalog_type_label 플레이스홀더가 없음")
    return template.safe_substitute(variables)


def _parse(content: str) -> LlmPhotoRecognitionResponse:
    try:
        return LlmPhotoRecognitionResponse.model_validate_json(_strip_markdown_fences(content))
    except ValidationError:
        logger.warning("사진 인식 LLM 응답 파싱 실패", exc_info=True)
        raise


def identify_photo(
    db: Session, catalog_type: CatalogType, image_bytes: bytes, image_content_type: str
) -> PhotoRecognitionResponse:
    template_text, providers = _resolve_prompt_and_providers(db)

    candidates_by_id, candidates_text = _build_candidates(db, catalog_type)
    if not candidates_by_id:
        detail = f"catalog_type={catalog_type}에 해당하는 도감 후보가 없습니다"
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=detail)

    system_content = _render_system_prompt(template_text, candidates_text, catalog_type)
    image_input = ImageInput(
        base64_data=base64.b64encode(image_bytes).decode("ascii"),
        mime_type=image_content_type,
    )

    started_at = time.perf_counter()
    try:
        parsed, provider, model = call_with_fallback(
            providers=providers,
            system=system_content,
            prompt=PHOTO_RECOGNITION_USER_MESSAGE,
            parse=_parse,
            response_format=_PHOTO_RECOGNITION_RESPONSE_SCHEMA,
            images=[image_input],
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
    elapsed_ms = int((time.perf_counter() - started_at) * 1000)

    accepted_id = _judge_match(parsed, candidates_by_id)
    logger.info(
        "사진 인식 결과: catalog_type=%s provider=%s model=%s elapsed_ms=%d matched=%s "
        "confidence=%s accepted_id=%s observation=%s",
        catalog_type,
        provider,
        model,
        elapsed_ms,
        parsed.matched,
        parsed.confidence,
        accepted_id,
        parsed.observation.replace("\n", " "),
    )
    if accepted_id is None:
        return PhotoRecognitionResponse(
            matched=False, catalog_type=catalog_type, catalog_id=None, name=None
        )
    return PhotoRecognitionResponse(
        matched=True,
        catalog_type=catalog_type,
        catalog_id=accepted_id,
        name=candidates_by_id[accepted_id],
    )
