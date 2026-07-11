import logging
from datetime import datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

import requests

from app.core.config import get_settings

logger = logging.getLogger(__name__)

KMA_BASE_URL = "https://apis.data.go.kr/1360000/VilageFcstInfoService_2.0"
WEATHER_PLACE_NAME = "어린이대공원"
KST = ZoneInfo("Asia/Seoul")

# 서울어린이대공원(광진구 능동로 216, 대략 위도 37.548~37.552 / 경도 127.07 범위) 대표 좌표 후보
# 여러 개를 기상청 공식 위경도<->격자 변환(람베르트 정형 원추 투영법) 공식에 넣었을 때 모두 같은
# 격자로 수렴한 값이다. 기상청 API허브의 공식 "동네예보 격자번호 조회" 도구로는 아직 재확인되지
# 않았다 — 격자가 틀리면 에러 없이 다른 지역의 날씨가 조용히 반환되므로, 구현 시 반드시
# https://apihub.kma.go.kr 에서 재검증한다(Step 3 수동 검증 참고).
GRID_NX = 62
GRID_NY = 126

PTY_LABELS = {
    "0": "없음",
    "1": "비",
    "2": "비/눈",
    "3": "눈",
    "4": "소나기",
    "5": "빗방울",
    "6": "빗방울눈날림",
    "7": "눈날림",
}
SKY_LABELS = {"1": "맑음", "3": "구름많음", "4": "흐림"}

_VILAGE_FCST_RELEASE_HOURS = (2, 5, 8, 11, 14, 17, 20, 23)


def _latest_ultra_srt_ncst_base(now: datetime) -> tuple[str, str]:
    """초단기실황은 매시 40분에 발표되고 발표 후 몇 분 뒤 제공된다.
    45분 버퍼를 둬 아직 제공되지 않았을 수 있는 이번 시각 대신 이전 시각 값을 요청한다."""
    base_dt = now if now.minute >= 45 else now - timedelta(hours=1)
    return base_dt.strftime("%Y%m%d"), base_dt.strftime("%H00")


def _latest_vilage_fcst_base(now: datetime) -> tuple[str, str]:
    """단기예보는 하루 8회(02/05/08/11/14/17/20/23시) 발표되고 약 10분 뒤 제공된다.
    15분 버퍼를 둬 가장 최근에 확실히 제공된 발표 시각을 역산한다."""
    candidate = now - timedelta(minutes=15)
    available_hours = [h for h in _VILAGE_FCST_RELEASE_HOURS if h <= candidate.hour]
    if available_hours:
        base_hour = max(available_hours)
        base_date = candidate.strftime("%Y%m%d")
    else:
        base_hour = _VILAGE_FCST_RELEASE_HOURS[-1]
        base_date = (candidate - timedelta(days=1)).strftime("%Y%m%d")
    return base_date, f"{base_hour:02d}00"


def _request_kma_api(endpoint: str, extra_params: dict[str, str | int]) -> list[dict[str, Any]]:
    settings = get_settings()
    params: dict[str, str | int] = {
        "serviceKey": settings.data_go_kr_service_key,
        "dataType": "JSON",
        "numOfRows": 1000,
        "pageNo": 1,
    }
    params.update(extra_params)
    try:
        response = requests.get(f"{KMA_BASE_URL}/{endpoint}", params=params, timeout=10)
        response.raise_for_status()
        payload = response.json()["response"]
    except requests.RequestException as exc:
        status = getattr(exc.response, "status_code", "unknown")
        raise RuntimeError(f"기상청 {endpoint} API 호출 실패 (status={status})") from None
    result_code = payload["header"]["resultCode"]
    if result_code != "00":
        result_msg = payload["header"]["resultMsg"]
        raise RuntimeError(
            f"기상청 {endpoint} 응답 오류 (resultCode={result_code}, resultMsg={result_msg})"
        )
    items = payload["body"]["items"]["item"]
    return items if isinstance(items, list) else [items]


def fetch_current_observation() -> dict[str, Any]:
    base_date, base_time = _latest_ultra_srt_ncst_base(datetime.now(KST))
    items = _request_kma_api(
        "getUltraSrtNcst",
        {"base_date": base_date, "base_time": base_time, "nx": GRID_NX, "ny": GRID_NY},
    )
    values = {item["category"]: item["obsrValue"] for item in items}
    observed_at = datetime.strptime(f"{base_date}{base_time}", "%Y%m%d%H%M").replace(tzinfo=KST)
    return {
        "temperature": float(values["T1H"]),
        "humidity": int(values["REH"]),
        "precipitation_type": PTY_LABELS.get(values["PTY"], values["PTY"]),
        "wind_speed": float(values["WSD"]),
        "observed_at": observed_at,
    }


def fetch_hourly_forecast() -> list[dict[str, Any]]:
    base_date, base_time = _latest_vilage_fcst_base(datetime.now(KST))
    items = _request_kma_api(
        "getVilageFcst",
        {"base_date": base_date, "base_time": base_time, "nx": GRID_NX, "ny": GRID_NY},
    )
    grouped: dict[tuple[str, str], dict[str, str]] = {}
    for item in items:
        key = (item["fcstDate"], item["fcstTime"])
        grouped.setdefault(key, {})[item["category"]] = item["fcstValue"]

    forecast: list[dict[str, Any]] = []
    last_sky: str | None = None
    last_pty: str | None = None
    for (fcst_date, fcst_time), values in sorted(grouped.items()):
        sky = values.get("SKY", last_sky)
        pty = values.get("PTY", last_pty)
        last_sky, last_pty = sky, pty
        if "TMP" not in values:
            continue
        forecast.append(
            {
                "datetime": datetime.strptime(f"{fcst_date}{fcst_time}", "%Y%m%d%H%M")
                .replace(tzinfo=KST)
                .isoformat(),
                "temperature": float(values["TMP"]),
                "precipitation_probability": int(values.get("POP", 0)),
                "precipitation_type": PTY_LABELS.get(pty, pty) if pty else "없음",
                "sky_condition": SKY_LABELS.get(sky, sky) if sky else None,
            }
        )
    return forecast


def fetch_weather_from_kma_api() -> dict[str, Any]:
    observation = fetch_current_observation()
    hourly_forecast = fetch_hourly_forecast()
    # 초단기실황(observation)에는 SKY(하늘상태) 필드가 없다. 가장 가까운 단기예보 시간대의
    # sky_condition을 "현재" 하늘상태로 대체 사용한다(hourly_forecast는 시간순 정렬되어 있어
    # 첫 항목이 가장 가까운 미래 시각). 예보가 비어 있으면 None으로 둔다.
    sky_condition = hourly_forecast[0]["sky_condition"] if hourly_forecast else None
    return {**observation, "sky_condition": sky_condition, "hourly_forecast": hourly_forecast}
