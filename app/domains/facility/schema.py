from pydantic import BaseModel, ConfigDict, field_validator

from app.core.kst import KstDatetime


class FacilityResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    external_id: int
    category: str
    name: str
    intro: str | None
    description: str | None
    latitude: float | None
    longitude: float | None
    facility_type: str | None
    updated_at: KstDatetime


class OperatingHoursSectionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    section_title: str
    content_html: str
    display_order: int
    collected_at: KstDatetime


class AmusementRideCreate(BaseModel):
    name: str
    description: str | None = None
    location: str | None = None
    is_active: bool = True


class AmusementRideUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    location: str | None = None
    is_active: bool | None = None

    # DB 컬럼이 NOT NULL이라 필드가 명시적으로 전달됐을 때 null이면 거부한다
    # (필드 생략 시에는 검증기가 호출되지 않아 부분 업데이트에는 영향 없음)
    @field_validator("name")
    @classmethod
    def name_must_not_be_null(cls, value: str | None) -> str | None:
        if value is None:
            raise ValueError("name must not be null")
        return value

    @field_validator("is_active")
    @classmethod
    def is_active_must_not_be_null(cls, value: bool | None) -> bool | None:
        if value is None:
            raise ValueError("is_active must not be null")
        return value


class AmusementRideResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None
    location: str | None
    is_active: bool
    updated_at: KstDatetime
