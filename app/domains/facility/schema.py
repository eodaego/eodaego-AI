from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.kst import KstDatetime

_RIDE_NAME_DESC = "놀이기구 이름. DB 유니크 제약이 있다."


class FacilityResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int = Field(description="시설 항목 PK")
    external_id: int = Field(description="원본 데이터 출처 시스템의 ID (유니크)")
    category: str = Field(description="시설 분류 (원본 데이터 값 그대로)")
    name: str = Field(description="시설 이름")
    intro: str | None = Field(description="간단 소개. 없으면 null.")
    description: str | None = Field(description="상세 설명. 없으면 null.")
    latitude: float | None = Field(description="위도. 좌표 정보가 없는 시설은 null.")
    longitude: float | None = Field(description="경도. 좌표 정보가 없는 시설은 null.")
    facility_type: str | None = Field(description="세부 시설 유형. 없으면 null.")
    updated_at: KstDatetime = Field(description="마지막 수정 시각 (KST)")


class OperatingHoursSectionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int = Field(description="운영시간 안내 섹션 PK")
    section_title: str = Field(description="섹션 제목")
    content_html: str = Field(
        description="원본 페이지의 HTML 조각을 그대로 저장한 값 (별도 sanitize 없음 — "
        "BE/FE에서 렌더링 시 필요하면 직접 처리)"
    )
    display_order: int = Field(description="노출 순서 (오름차순 정렬 기준)")
    collected_at: KstDatetime = Field(
        description="수집 시각 (KST). `crawl_operating_hours` job은 매 수집 시 기존 섹션을 "
        "전체 삭제 후 재삽입하므로(upsert 아님), 크롤링마다 id가 바뀔 수 있다."
    )


class AmusementRideCreate(BaseModel):
    name: str = Field(
        description=f"{_RIDE_NAME_DESC} 생성 시 중복이면 409 Conflict를 반환한다.",
        examples=["회전목마"],
    )
    description: str | None = Field(default=None, description="설명. 생략 시 null.")
    location: str | None = Field(default=None, description="위치 설명. 생략 시 null.")
    is_active: bool = Field(default=True, description="운영 여부")


class AmusementRideUpdate(BaseModel):
    name: str | None = Field(
        default=None,
        description=(
            f"{_RIDE_NAME_DESC} 필드를 생략하면 기존 값 유지, 명시적으로 null을 보내면 "
            "422(DB NOT NULL 제약 반영). 수정 결과 다른 놀이기구와 이름이 중복되면 "
            "500이 발생한다(POST와 달리 IntegrityError를 잡지 않아 409로 매핑되지 않음)."
        ),
    )
    description: str | None = Field(default=None, description="설명. 생략 시 기존 값 유지.")
    location: str | None = Field(default=None, description="위치 설명. 생략 시 기존 값 유지.")
    is_active: bool | None = Field(
        default=None,
        description="운영 여부. 필드를 생략하면 기존 값 유지, 명시적으로 null을 보내면 "
        "422(DB NOT NULL 제약 반영).",
    )

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

    id: int = Field(description="놀이기구 PK")
    name: str = Field(description=_RIDE_NAME_DESC)
    description: str | None = Field(description="설명. 없으면 null.")
    location: str | None = Field(description="위치 설명. 없으면 null.")
    is_active: bool = Field(description="운영 여부")
    updated_at: KstDatetime = Field(description="마지막 수정 시각 (KST)")
