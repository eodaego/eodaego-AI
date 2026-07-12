from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.core.kst import KstDatetime

_JOB_ID_DESC = (
    "실행할 크롤링 작업 식별자. 아래 4개 값 중 하나여야 실제로 스케줄러에 등록된다 "
    "(그 외 값은 저장은 되지만 다음 서버 재시작 시 조용히 스킵됨): "
    "`crawl_congestion`(혼잡도), `crawl_catalog`(동식물 도감), "
    "`crawl_operating_hours`(운영시간), `crawl_weather`(날씨). "
    "DB 유니크 제약이 있으며 중복 시 500이 발생한다(별도 409 처리 없음)."
)
_TRIGGER_TYPE_DESC = "interval: 일정 간격 반복 실행 / cron: crontab 표현식 기반 실행"
_TRIGGER_CONFIG_DESC = (
    "trigger_type에 따라 형식이 다르며 저장 시점에는 형식을 검증하지 않는다(잘못된 값은 "
    "다음 서버 재시작 시 경고 로그만 남기고 등록이 스킵됨). "
    'interval: "{minutes|hours}={정수}" 형식(예: "minutes=30", "hours=1"). '
    'cron: 표준 5필드 crontab 표현식(예: "*/10 * * * *").'
)
_IS_ACTIVE_DESC = (
    "true여야 다음 AI 서버 재시작 시 스케줄러에 등록된다. 이 값을 바꿔도 이미 실행 중인 "
    "스케줄러에는 즉시 반영되지 않는다."
)


class ScheduleConfigCreate(BaseModel):
    job_id: str = Field(description=_JOB_ID_DESC, examples=["crawl_congestion"])
    trigger_type: Literal["interval", "cron"] = Field(description=_TRIGGER_TYPE_DESC)
    trigger_config: str = Field(description=_TRIGGER_CONFIG_DESC, examples=["minutes=30"])
    is_active: bool = Field(default=True, description=_IS_ACTIVE_DESC)


class ScheduleConfigUpdate(BaseModel):
    trigger_type: Literal["interval", "cron"] | None = Field(
        default=None,
        description=(f"{_TRIGGER_TYPE_DESC} 생략 시 기존 값 유지. job_id는 수정할 수 없다."),
    )
    trigger_config: str | None = Field(
        default=None,
        description=f"{_TRIGGER_CONFIG_DESC} 생략 시 기존 값 유지.",
    )
    is_active: bool | None = Field(
        default=None,
        description=f"{_IS_ACTIVE_DESC} 생략 시 기존 값 유지.",
    )


class ScheduleConfigResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int = Field(description="스케줄 설정 PK")
    job_id: str = Field(description=_JOB_ID_DESC)
    trigger_type: str = Field(description=_TRIGGER_TYPE_DESC)
    trigger_config: str = Field(description=_TRIGGER_CONFIG_DESC)
    is_active: bool = Field(description=_IS_ACTIVE_DESC)
    updated_at: KstDatetime = Field(description="마지막 수정 시각 (KST)")


class CongestionSnapshotResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int = Field(description="혼잡도 스냅샷 PK")
    place_ref_key: str = Field(description="장소 식별 키 (현재는 '어린이대공원' 고정값)")
    congestion_level: str = Field(
        description="서울시 실시간 도시데이터 API의 AREA_CONGEST_LVL 원본 값 "
        "(이 서버는 값 집합을 검증·제한하지 않고 그대로 저장한다)"
    )
    congestion_message: str = Field(description="혼잡도 설명 메시지 원문 (AREA_CONGEST_MSG)")
    population_min: int = Field(description="실시간 추정 인구 최솟값 (AREA_PPLTN_MIN)")
    population_max: int = Field(description="실시간 추정 인구 최댓값 (AREA_PPLTN_MAX)")
    forecast: list[dict[str, Any]] = Field(
        description="서울시 API의 FCST_PPLTN(인구 예측) 배열을 가공 없이 그대로 저장한 값. "
        "이 서버가 내부 필드 구성을 고정하지 않으므로 서울시 API 응답 형식을 그대로 따른다."
    )
    collected_at: KstDatetime = Field(description="수집 시각 (KST)")
