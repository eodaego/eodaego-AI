import base64
import logging
from string import Template

from fastapi import HTTPException, status
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domains.ai.suh_aider_client import call_chat
from app.domains.catalog.model import Animal, Plant
from app.domains.catalog.service import list_animals, list_plants
from app.domains.facility.model import Facility
from app.domains.prompt.service import get_active_prompt_template
from app.domains.recognition.schema import (
    CatalogType,
    LlmPhotoRecognitionResponse,
    PhotoRecognitionResponse,
)

logger = logging.getLogger(__name__)

_MAX_ATTEMPTS = 2  # 최초 시도 + 1회 재시도
_PLACE_FACILITY_TYPES = ("문화", "음식", "카페")
_MAX_DESCRIPTION_LENGTH_IN_PROMPT = (
    200  # 도감 데이터의 자유 텍스트 설명이 프롬프트를 과도하게 지배하지 않도록 제한
)
_PHOTO_RECOGNITION_PROMPT_TRIGGER = (
    "위 지침과 후보 목록을 참고해 첨부된 사진이 후보 중 어느 항목에 해당하는지 판단하고, "
    "지정된 JSON 스키마 형식으로만 응답하라. 후보 중 어느 것과도 일치하지 않거나 판단하기 "
    "어려우면 matched를 false로, catalog_id를 null로 응답하라."
)
_PHOTO_RECOGNITION_RESPONSE_SCHEMA = LlmPhotoRecognitionResponse.model_json_schema()


def _format_animal_candidate(animal: Animal) -> str:
    return (
        f"- id={animal.id}, name={animal.name}, "
        f"scientific_name={animal.scientific_name or '정보없음'}, "
        f"english_name={animal.english_name or '정보없음'}, "
        f"distribution={animal.distribution or '정보없음'}, "
        f"diet={animal.diet or '정보없음'}"
    )


def _format_plant_candidate(plant: Plant) -> str:
    description = (plant.description or "정보없음")[:_MAX_DESCRIPTION_LENGTH_IN_PROMPT]
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
    stmt = select(Facility).where(Facility.facility_type.in_(_PLACE_FACILITY_TYPES))
    facilities = list(db.scalars(stmt).all())
    candidates_by_id = {f.id: f.name for f in facilities}
    candidates_text = "\n".join(_format_place_candidate(f) for f in facilities)
    return candidates_by_id, candidates_text


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


def identify_photo(
    db: Session, catalog_type: CatalogType, image_bytes: bytes
) -> PhotoRecognitionResponse:
    prompt = get_active_prompt_template(db, purpose="photo_recognition")
    if prompt is None:
        detail = "활성화된 사진 인식 프롬프트가 없습니다"
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=detail)

    candidates_by_id, candidates_text = _build_candidates(db, catalog_type)
    if not candidates_by_id:
        detail = f"catalog_type={catalog_type}에 해당하는 도감 후보가 없습니다"
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=detail)

    variables = {"candidates": candidates_text}
    template = Template(prompt.template_text)
    missing_vars = template.get_identifiers() - variables.keys()
    if missing_vars:
        logger.warning(
            "사진 인식 프롬프트 템플릿에 채워지지 않은 변수가 있음(오래된 플레이스홀더일 "
            "가능성): %s",
            sorted(missing_vars),
        )
    system_content = template.safe_substitute(variables)
    image_base64 = base64.b64encode(image_bytes).decode("ascii")

    last_error = RuntimeError("사진 인식 실패")
    for _ in range(_MAX_ATTEMPTS):
        try:
            content = call_chat(
                model=prompt.model,
                system=system_content,
                prompt=_PHOTO_RECOGNITION_PROMPT_TRIGGER,
                response_format=_PHOTO_RECOGNITION_RESPONSE_SCHEMA,
                images=[image_base64],
            )
            parsed = LlmPhotoRecognitionResponse.model_validate_json(
                _strip_markdown_fences(content)
            )
        except ValidationError as exc:
            logger.warning("사진 인식 LLM 응답 파싱 실패", exc_info=True)
            last_error = RuntimeError(f"사진 인식 LLM 응답 파싱 실패: {exc}")
            continue
        except RuntimeError as exc:
            last_error = exc
            continue

        if parsed.matched and parsed.catalog_id in candidates_by_id:
            return PhotoRecognitionResponse(
                matched=True,
                catalog_type=catalog_type,
                catalog_id=parsed.catalog_id,
                name=candidates_by_id[parsed.catalog_id],
            )
        return PhotoRecognitionResponse(
            matched=False, catalog_type=catalog_type, catalog_id=None, name=None
        )

    raise HTTPException(
        status_code=status.HTTP_502_BAD_GATEWAY, detail=str(last_error)
    ) from last_error
