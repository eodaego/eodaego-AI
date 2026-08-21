from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.core.openapi import COMMON_ERRORS, error_response
from app.core.security import verify_internal_api_key
from app.db.session import get_db
from app.domains.recognition import service
from app.domains.recognition.schema import CatalogType, PhotoRecognitionResponse

router = APIRouter(
    prefix="/api/v1/recognition",
    tags=["recognition"],
    dependencies=[Depends(verify_internal_api_key)],
)

_MAX_IMAGE_SIZE_BYTES = 10 * 1024 * 1024  # 10MB


@router.post(
    "/identify",
    response_model=PhotoRecognitionResponse,
    summary="사진 기반 동식물·장소 도감 인식",
    responses={
        **COMMON_ERRORS,
        422: error_response(
            "UNPROCESSABLE_ENTITY",
            "image는 image/* 형식이어야 하고 10MB를 초과할 수 없습니다",
            "요청 스키마 자체가 잘못됐을 때(COMMON_ERRORS의 VALIDATION_ERROR)도 이 상태 코드가 "
            "나올 수 있다. 이 문서 예시는 image의 Content-Type이 image/*가 아니거나 크기가 "
            "10MB를 초과하는 경우, 또는 catalog_type에 해당하는 도감 후보가 0건인 경우다",
        ),
        503: error_response(
            "SERVICE_UNAVAILABLE",
            "활성화된 사진 인식 프롬프트가 없습니다",
            "purpose='photo_recognition'이고 is_active=true인 프롬프트 템플릿이 하나도 없음 — "
            "POST 또는 PATCH /api/v1/prompts로 먼저 활성 템플릿을 만들어야 함",
        ),
        502: error_response(
            "BAD_GATEWAY",
            "구성된 LLM provider 호출이 모두 실패했습니다",
            "활성 프롬프트 템플릿에 등록된 LLM provider(우선순위 순)를 각 1회씩 시도했지만 "
            "모두 호출 실패했거나 응답을 기대한 구조(matched/catalog_id)로 파싱하지 못함",
        ),
    },
)
def identify_photo(
    catalog_type: Annotated[CatalogType, Form(description="인식 대상 도감 타입.")],
    image: Annotated[UploadFile, File(description="인식할 사진 파일.")],
    db: Session = Depends(get_db),
) -> PhotoRecognitionResponse:
    """BE가 지정한 `catalog_type`에 해당하는 도감 후보(ANIMAL=Animal 전체, PLANT=Plant 전체,
    PLACE=Facility 중 facility_type이 '문화'/'음식'/'카페'인 데이터) 중 첨부된 사진이 어느
    항목과 일치하는지 판단한다. 매칭 실패는 에러가 아닌 `matched=false` 응답으로 처리한다.
    """
    if image.content_type is None or not image.content_type.startswith("image/"):
        detail = "image는 image/* 형식이어야 합니다"
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=detail)

    image_bytes = image.file.read(_MAX_IMAGE_SIZE_BYTES + 1)
    if len(image_bytes) > _MAX_IMAGE_SIZE_BYTES:
        detail = "image 크기는 10MB를 초과할 수 없습니다"
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=detail)

    return service.identify_photo(db, catalog_type, image_bytes, image.content_type)
