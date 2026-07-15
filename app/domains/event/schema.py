from datetime import date

from pydantic import BaseModel, ConfigDict, Field

from app.core.kst import KstDatetime


class CulturalEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int = Field(description="행사 PK")
    title: str = Field(description="행사명")
    place: str = Field(description="장소 (서울시 API 원본 텍스트, 예: '어린이대공원 X경기장')")
    start_date: date = Field(description="시작일")
    end_date: date = Field(description="종료일")
    description: str | None = Field(description="행사 설명/프로그램")
    target: str | None = Field(description="이용대상")
    fee: str | None = Field(description="이용요금")
    homepage_url: str | None = Field(description="홈페이지 URL")
    updated_at: KstDatetime = Field(description="마지막 동기화 시각 (KST)")
