from typing import Literal

from pydantic import BaseModel, Field

PreferenceTag = Literal["ANIMAL_FRIENDLY", "PLANT_FRIENDLY", "ACTIVITY", "LEARNING"]

_PREFERENCE_TAGS_DESC = (
    "추천 동선에 반영할 선호 태그. 복수 선택 가능하며, 선택된 태그가 매핑된 "
    "Facility.category 전체가 후보로 모인다 "
    "(ANIMAL_FRIENDLY→동물나라, PLANT_FRIENDLY→자연나라/조경시설, "
    "ACTIVITY→재미나라/체험시설/운동 및 대관시설, "
    "LEARNING→동물나라/자연나라(도감 항목을 볼 수 있는 장소))."
)


class RecommendationRoutesRequest(BaseModel):
    preference_tags: list[PreferenceTag] = Field(
        description=_PREFERENCE_TAGS_DESC,
        examples=[["ANIMAL_FRIENDLY", "ACTIVITY"]],
        min_length=1,
    )
    stay_duration_minutes: int = Field(description="예상 체류 시간(분).", examples=[120], gt=0)
    start_location: str = Field(
        description="시작 위치(자유 텍스트, 예: 정문/후문).", examples=["정문"], max_length=100
    )
    with_children: bool = Field(description="어린이 동반 여부.", examples=[True])


class RouteStop(BaseModel):
    facility_id: int = Field(description="추천된 시설(Facility)의 PK.")
    order: int = Field(description="이 코스 내 방문 순서(1부터 시작).", ge=1)


class RecommendedCourse(BaseModel):
    title: str = Field(description="코스 제목.")
    reason: str = Field(description="이 코스를 추천하는 이유.")
    stops: list[RouteStop] = Field(description="방문 순서대로 정렬된 정류지 목록.")


class RecommendationRoutesResponse(BaseModel):
    courses: list[RecommendedCourse] = Field(description="추천 코스 목록.")
