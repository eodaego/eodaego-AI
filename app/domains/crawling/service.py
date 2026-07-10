import logging
from typing import Any
from urllib.parse import quote

import requests
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings
from app.db.session import get_engine
from app.domains.crawling.model import CongestionSnapshot, ScheduleConfig
from app.domains.crawling.schema import ScheduleConfigCreate, ScheduleConfigUpdate


def create_schedule_config(db: Session, data: ScheduleConfigCreate) -> ScheduleConfig:
    schedule = ScheduleConfig(**data.model_dump())
    db.add(schedule)
    db.commit()
    db.refresh(schedule)
    return schedule


def list_schedule_configs(db: Session) -> list[ScheduleConfig]:
    return list(db.scalars(select(ScheduleConfig)).all())


def get_schedule_config(db: Session, schedule_id: int) -> ScheduleConfig | None:
    return db.get(ScheduleConfig, schedule_id)


def update_schedule_config(
    db: Session, schedule: ScheduleConfig, data: ScheduleConfigUpdate
) -> ScheduleConfig:
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(schedule, field, value)
    db.commit()
    db.refresh(schedule)
    return schedule


def delete_schedule_config(db: Session, schedule: ScheduleConfig) -> None:
    db.delete(schedule)
    db.commit()


logger = logging.getLogger(__name__)

CONGESTION_PLACE_NAME = "어린이대공원"
CITYDATA_BASE_URL = "http://openapi.seoul.go.kr:8088"


def fetch_congestion_from_seoul_api() -> dict[str, Any]:
    settings = get_settings()
    place = quote(CONGESTION_PLACE_NAME)
    url = f"{CITYDATA_BASE_URL}/{settings.seoul_open_api_key}/json/citydata/1/5/{place}"
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    data = response.json()
    live_status: dict[str, Any] = data["CITYDATA"]["LIVE_PPLTN_STTS"][0]
    return live_status


def save_congestion_snapshot(db: Session, live_status: dict[str, Any]) -> CongestionSnapshot:
    snapshot = CongestionSnapshot(
        place_ref_key=CONGESTION_PLACE_NAME,
        congestion_level=live_status["AREA_CONGEST_LVL"],
        congestion_message=live_status["AREA_CONGEST_MSG"],
        population_min=int(live_status["AREA_PPLTN_MIN"]),
        population_max=int(live_status["AREA_PPLTN_MAX"]),
        forecast=live_status.get("FCST_PPLTN", []),
    )
    db.add(snapshot)
    db.commit()
    db.refresh(snapshot)
    return snapshot


def list_congestion_snapshots(db: Session, limit: int = 20) -> list[CongestionSnapshot]:
    stmt = select(CongestionSnapshot).order_by(CongestionSnapshot.collected_at.desc()).limit(limit)
    return list(db.scalars(stmt).all())


def crawl_congestion_job() -> None:
    session_factory = sessionmaker(bind=get_engine())
    with session_factory() as db:
        try:
            live_status = fetch_congestion_from_seoul_api()
            save_congestion_snapshot(db, live_status)
        except Exception:
            db.rollback()
            logger.warning("혼잡도 수집 실패", exc_info=True)
