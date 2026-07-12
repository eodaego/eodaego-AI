from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.core.kst import KstDatetime

_HOURLY_FORECAST_EXAMPLE = [
    {
        "datetime": "2026-07-12T15:00:00",
        "temperature": 27.5,
        "precipitation_probability": 20,
        "precipitation_type": "없음",
        "sky_condition": "맑음",
    }
]


class WeatherSnapshotResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int = Field(description="날씨 스냅샷 PK")
    place_ref_key: str = Field(description="장소 식별 키 (현재는 '어린이대공원' 고정값)")
    temperature: float = Field(description="기온(섭씨). 기상청 초단기실황 관측값.")
    humidity: int = Field(description="습도(%)")
    precipitation_type: str = Field(
        description="강수 형태 한글 라벨. `app/domains/weather/service.py`의 PTY_LABELS "
        "매핑 값(없음, 비, 비/눈, 눈, 소나기, 빗방울, 빗방울눈날림, 눈날림)이 기본이지만, "
        "기상청이 매핑에 없는 코드를 내려주면 원본 코드 문자열이 그대로 노출될 수 있다."
    )
    wind_speed: float = Field(description="풍속(m/s)")
    sky_condition: str | None = Field(
        description="하늘상태 한글 라벨 (맑음/구름많음/흐림). 초단기실황 자체에는 하늘상태가 "
        "없어 가장 가까운 단기예보 값을 대체 사용하며, 예보가 비어 있으면 null."
    )
    hourly_forecast: list[dict[str, Any]] = Field(
        description="시간대별 예보 배열. 각 항목은 "
        "{datetime, temperature, precipitation_probability, precipitation_type, sky_condition} "
        "형태이며 시간순으로 정렬돼 있다.",
        examples=[_HOURLY_FORECAST_EXAMPLE],
    )
    observed_at: KstDatetime = Field(description="기상청 관측 기준 시각 (KST)")
    collected_at: KstDatetime = Field(description="이 서버가 수집(저장)한 시각 (KST)")
