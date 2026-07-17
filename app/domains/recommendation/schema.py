from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.core.kst import KstDatetime

PreferenceTag = Literal[
    "ANIMAL", "NATURE", "ACTIVITY", "PHOTO_SPOT", "RELAXATION", "CULTURE_EVENT", "LEARNING"
]
CompanionType = Literal["ALONE", "WITH_CHILD", "WITH_PARTNER", "WITH_FRIENDS", "WITH_ELDERLY"]
GateCode = Literal[
    "MAIN_GATE",
    "HOEGWAN_GATE",
    "SOUTH_GATE",
    "GUI_GATE",
    "EAST_GATE_1",
    "EAST_GATE_2",
    "REAR_GATE",
    "NORTH_GATE_1",
    "NORTH_GATE_2",
    "WEST_GATE",
    "NEUNGDONG_GATE",
]

_PREFERENCE_TAGS_DESC = (
    "추천 동선에 반영할 취향 태그. 복수 선택 가능, 선택하지 않거나(생략) 빈 배열이면 매핑된 "
    "모든 카테고리를 후보로 사용해 폭넓게 추천한다. 태그 → Facility.category 매핑은 관리자가 "
    "GET/POST/DELETE /api/v1/recommendation/preference-mappings로 직접 관리하며(초기 데이터는 "
    "ANIMAL/NATURE/ACTIVITY/RELAXATION만 매핑되어 있다), 매핑 테이블 자체가 비어 있으면 추천 "
    "후보 0건(422)이 될 수 있다."
)
_STAY_DURATION_MINUTES_DESC = "예상 체류 시간(분). 선택하지 않으면 프롬프트에서 이 조건이 생략된다."
_COMPANION_TYPE_DESC = (
    "동반자 유형. 단일 선택. ALONE(혼자 방문)/WITH_CHILD(아이와 함께)/"
    "WITH_PARTNER(연인과 함께)/WITH_FRIENDS(친구와 함께)/WITH_ELDERLY(어르신과 함께). "
    "선택하지 않으면 프롬프트에서 이 조건이 생략된다."
)
_GATE_CODE_DESC = (
    '서울어린이대공원 실제 출입구의 영문 코드. Facility(category="출입문").code와 매칭된다.'
)


class RecommendationRoutesRequest(BaseModel):
    preference_tags: list[PreferenceTag] | None = Field(
        default=None,
        description=_PREFERENCE_TAGS_DESC,
        examples=[["ANIMAL", "ACTIVITY"]],
    )
    stay_duration_minutes: int | None = Field(
        default=None, description=_STAY_DURATION_MINUTES_DESC, examples=[120], gt=0
    )
    entrance_facility_code: GateCode = Field(
        description=f"입구로 사용할 출입구 코드. {_GATE_CODE_DESC}", examples=["MAIN_GATE"]
    )
    exit_facility_code: GateCode = Field(
        description=f"출구로 사용할 출입구 코드. {_GATE_CODE_DESC}", examples=["SOUTH_GATE"]
    )
    companion_type: CompanionType | None = Field(
        default=None, description=_COMPANION_TYPE_DESC, examples=["WITH_CHILD"]
    )


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


# LLM 원시 응답 파싱 전용 내부 스키마 — 공개 응답 스키마(RouteStop/RecommendedCourse)와 달리
# 입구/출구를 제외한 중간 방문지 facility_id만 순서 무관하게 담는다. 실제 방문 순서는
# route_optimizer.optimize_route()가 좌표 기반으로 계산한 뒤 서비스가 조립한다.
class LlmCourse(BaseModel):
    title: str = Field(description="코스 제목.")
    reason: str = Field(description="이 코스를 추천하는 이유.")
    facility_ids: list[int] = Field(
        description="입구/출구를 제외한 중간 방문지 facility_id 목록(순서 무관)."
    )


class LlmRecommendationResponse(BaseModel):
    courses: list[LlmCourse] = Field(description="LLM이 구성한 코스 목록(방문 순서 미포함).")


class PreferenceCategoryMappingCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    preference_tag: PreferenceTag = Field(description="매핑할 취향 태그.", examples=["ANIMAL"])
    category: str = Field(
        description="매핑할 Facility.category 값. 앞뒤 공백은 자동으로 제거된다.",
        examples=["동물나라"],
        min_length=1,
        max_length=50,
    )


class PreferenceCategoryMappingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int = Field(description="매핑 PK")
    preference_tag: str = Field(
        description="매핑된 취향 태그. 생성 시(POST)에는 PreferenceTag 7종으로 제한되지만, 이 "
        "응답 필드는 DB에 남아있을 수 있는 값을 안전하게 직렬화하기 위해 str로 완화되어 있다."
    )
    category: str = Field(description="매핑된 Facility.category 값")
    updated_at: KstDatetime = Field(description="마지막 수정 시각 (KST)")
