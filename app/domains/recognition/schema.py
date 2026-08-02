from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

CatalogType = Literal["ANIMAL", "PLANT", "PLACE"]

_CATALOG_TYPE_DESC = (
    "인식 대상 도감 타입. BE가 사진 촬영 대상을 미리 지정한다. "
    "PLACE는 Facility 중 facility_type이 '문화'/'음식'/'카페'인 데이터만 후보로 삼는다."
)

_CATALOG_ID_DESC = (
    "매칭된 도감 항목의 PK. catalog_type='ANIMAL'/'PLANT'/'PLACE'에 따라 각각 Animal.id/"
    "Plant.id/Facility.id를 가리킨다(테이블이 다르므로 catalog_type과 함께 해석해야 한다). "
    "matched=false이면 null."
)


class PhotoRecognitionResponse(BaseModel):
    matched: bool = Field(
        description="사진이 해당 catalog_type의 도감 데이터 중 하나와 매칭됐는지 여부."
    )
    catalog_type: CatalogType = Field(description=_CATALOG_TYPE_DESC)
    catalog_id: int | None = Field(description=_CATALOG_ID_DESC)
    name: str | None = Field(description="매칭된 항목의 이름. matched=false이면 null.")


# LLM 원시 응답 파싱 전용 내부 스키마. 공개 응답(PhotoRecognitionResponse)과 달리 name은
# 서비스가 candidate 목록에서 catalog_id로 되찾아 채우므로 LLM에게 요구하지 않는다.
class LlmPhotoRecognitionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    matched: bool = Field(description="사진이 후보 목록 중 하나와 매칭됐는지 여부.")
    catalog_id: int | None = Field(description="매칭된 후보의 id. matched=false이면 null.")
