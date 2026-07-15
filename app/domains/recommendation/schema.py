from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.core.kst import KstDatetime

PreferenceTag = Literal[
    "ANIMAL", "NATURE", "ACTIVITY", "PHOTO_SPOT", "RELAXATION", "CULTURE_EVENT", "LEARNING"
]
CompanionType = Literal["ALONE", "WITH_CHILD", "WITH_PARTNER", "WITH_FRIENDS", "WITH_ELDERLY"]

_PREFERENCE_TAGS_DESC = (
    "추천 동선에 반영할 취향 태그. 복수 선택 가능, 최소 1개 필요. 태그 → Facility.category "
    "매핑은 관리자가 GET/POST/DELETE /api/v1/recommendation/preference-mappings로 직접 "
    "관리하며(초기 데이터는 ANIMAL/NATURE/ACTIVITY/RELAXATION만 매핑되어 있다), 매핑이 하나도 "
    "없는 태그만 선택하면 추천 후보 0건(422)이 될 수 있다."
)
_COMPANION_TYPE_DESC = (
    "동반자 유형. 단일 선택. ALONE(혼자 방문)/WITH_CHILD(아이와 함께)/"
    "WITH_PARTNER(연인과 함께)/WITH_FRIENDS(친구와 함께)/WITH_ELDERLY(어르신과 함께)."
)


class RecommendationRoutesRequest(BaseModel):
    preference_tags: list[PreferenceTag] = Field(
        description=_PREFERENCE_TAGS_DESC,
        examples=[["ANIMAL", "ACTIVITY"]],
        min_length=1,
    )
    stay_duration_minutes: int = Field(description="예상 체류 시간(분).", examples=[120], gt=0)
    entrance_facility_id: int = Field(
        description='입구로 사용할 Facility(category="출입문")의 PK.', examples=[27]
    )
    exit_facility_id: int = Field(
        description='출구로 사용할 Facility(category="출입문")의 PK.', examples=[28]
    )
    companion_type: CompanionType = Field(description=_COMPANION_TYPE_DESC, examples=["WITH_CHILD"])


class RouteStop(BaseModel):
    facility_id: int = Field(description="추천된 시설(Facility)의 PK.")
    order: int = Field(description="이 코스 내 방문 순서(1부터 시작).", ge=1)


class RecommendedCourse(BaseModel):
    title: str = Field(description="코스 제목.")
    reason: str = Field(description="이 코스를 추천하는 이유.")
    stops: list[RouteStop] = Field(
        description="방문 순서대로 정렬된 정류지 목록(입구는 order=1, 출구는 마지막 order로 포함)."
    )


class RecommendationRoutesResponse(BaseModel):
    courses: list[RecommendedCourse] = Field(description="추천 코스 목록.")


class PreferenceCategoryMappingCreate(BaseModel):
    preference_tag: PreferenceTag = Field(description="매핑할 취향 태그.", examples=["ANIMAL"])
    category: str = Field(
        description="매핑할 Facility.category 값.",
        examples=["동물나라"],
        min_length=1,
        max_length=50,
    )


class PreferenceCategoryMappingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int = Field(description="매핑 PK")
    preference_tag: PreferenceTag = Field(description="매핑된 취향 태그")
    category: str = Field(description="매핑된 Facility.category 값")
    updated_at: KstDatetime = Field(description="마지막 수정 시각 (KST)")
