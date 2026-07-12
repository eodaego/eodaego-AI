from pydantic import BaseModel, ConfigDict, Field

from app.core.kst import KstDatetime

_MSG_SEQ_DESC = (
    "원본 게시판(서울시설공단 어린이대공원 도감) 글 번호. 이 서버 PK는 아니지만 원본 기준 "
    "유니크하며, 크롤링 upsert 시 이 값으로 신규/기존 항목을 판단한다."
)
_REGISTERED_DATE_DESC = "원본 게시판 등록일 문자열 그대로 (파싱된 date 타입이 아닌 원본 텍스트)"
_THUMBNAIL_URL_DESC = "썸네일 이미지 URL. 원본에 이미지가 없으면 null."
_SOURCE_URL_DESC = (
    "원본 상세 페이지 URL (값 자체는 목록 페이지 크롤링 시 msg_seq로 조합해 생성됨)"
)
_UPDATED_AT_DESC = "마지막 크롤링 upsert 시각 (KST)"
_CLASSIFICATION_DESC = "원본 목록 페이지 항목의 '분류' 라벨 값. 없으면 null."


class AnimalResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int = Field(description="동물 도감 항목 PK")
    msg_seq: int = Field(description=_MSG_SEQ_DESC)
    category: str = Field(description="분류: 포유류 / 조류 / 파충류 중 하나")
    name: str = Field(description="동물 이름")
    scientific_name: str | None = Field(
        description="학명. 원본 목록 페이지 항목에 해당 라벨이 없으면 null."
    )
    english_name: str | None = Field(description="영명. 라벨이 없으면 null.")
    classification: str | None = Field(description=_CLASSIFICATION_DESC)
    distribution: str | None = Field(description="분포. 라벨이 없으면 null.")
    diet: str | None = Field(description="먹는것(먹이). 라벨이 없으면 null.")
    registered_date: str | None = Field(description=_REGISTERED_DATE_DESC)
    thumbnail_url: str | None = Field(description=_THUMBNAIL_URL_DESC)
    location_name: str | None = Field(
        description="공공데이터포털 동물 위치 정보 API와 이름 매칭으로 동기화한 사육장 위치명. "
        "아직 동기화되지 않았거나 이름 매칭에 실패하면 null."
    )
    source_url: str = Field(description=_SOURCE_URL_DESC)
    updated_at: KstDatetime = Field(description=_UPDATED_AT_DESC)


class PlantResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int = Field(description="식물 도감 항목 PK")
    msg_seq: int = Field(description=_MSG_SEQ_DESC)
    category: str = Field(description="분류: 수목 / 관엽식물 / 다육식물 / 분재 / 야생화 중 하나")
    name: str = Field(description="식물 이름")
    description: str | None = Field(
        description="원본 목록 페이지 항목의 '■ 특징' 본문 텍스트. 없으면 null."
    )
    registered_date: str | None = Field(description=_REGISTERED_DATE_DESC)
    thumbnail_url: str | None = Field(description=_THUMBNAIL_URL_DESC)
    source_url: str = Field(description=_SOURCE_URL_DESC)
    updated_at: KstDatetime = Field(description=_UPDATED_AT_DESC)
