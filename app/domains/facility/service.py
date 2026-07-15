import logging
from typing import Any

import requests
from bs4 import BeautifulSoup
from sqlalchemy import delete, select
from sqlalchemy.orm import Session, sessionmaker

from app.core.job_lock import JobRunGuard
from app.core.schema import CrawlResult
from app.db.session import get_engine
from app.domains.facility.model import AmusementRide, Facility, OperatingHoursSection
from app.domains.facility.schema import (
    AmusementRideCreate,
    AmusementRideUpdate,
    FacilityCreate,
    FacilityUpdate,
)

logger = logging.getLogger(__name__)

USE_JSP_URL = "https://www.sisul.or.kr/open_content/childrenpark/introduce/use.jsp"


def list_facilities(db: Session, category: str | None = None) -> list[Facility]:
    stmt = select(Facility)
    if category is not None:
        stmt = stmt.where(Facility.category == category)
    return list(db.scalars(stmt).all())


def create_facility(db: Session, data: FacilityCreate) -> Facility:
    facility = Facility(**data.model_dump(), external_id=None)
    db.add(facility)
    db.commit()
    db.refresh(facility)
    return facility


def get_facility(db: Session, facility_id: int) -> Facility | None:
    return db.get(Facility, facility_id)


def get_facility_by_code(db: Session, code: str) -> Facility | None:
    return db.scalar(select(Facility).where(Facility.code == code))


def update_facility(db: Session, facility: Facility, data: FacilityUpdate) -> Facility:
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(facility, field, value)
    db.commit()
    db.refresh(facility)
    return facility


def delete_facility(db: Session, facility: Facility) -> None:
    db.delete(facility)
    db.commit()


def crawl_operating_hours() -> list[dict[str, Any]]:
    response = requests.get(USE_JSP_URL, timeout=10)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "lxml")
    sections: list[dict[str, Any]] = []
    for index, div in enumerate(soup.select("div#detail_con > div.para01")):
        title_tag = div.select_one("p.sblet")
        if title_tag is None:
            continue
        sections.append(
            {
                "section_title": title_tag.get_text(strip=True),
                "content_html": str(div),
                "display_order": index,
            }
        )
    return sections


def replace_operating_hours_sections(db: Session, sections: list[dict[str, Any]]) -> None:
    db.execute(delete(OperatingHoursSection))
    for section in sections:
        db.add(OperatingHoursSection(**section))
    db.commit()


def list_operating_hours_sections(db: Session) -> list[OperatingHoursSection]:
    stmt = select(OperatingHoursSection).order_by(OperatingHoursSection.display_order)
    return list(db.scalars(stmt).all())


def crawl_operating_hours_job() -> CrawlResult:
    with JobRunGuard("crawl_operating_hours"):
        session_factory = sessionmaker(bind=get_engine())
        with session_factory() as db:
            try:
                sections = crawl_operating_hours()
                if not sections:
                    logger.warning("운영시간 크롤링 결과가 비어있어 기존 데이터를 유지합니다")
                    return CrawlResult(
                        success=False,
                        collected_count=0,
                        message="크롤링 결과가 비어있음",
                    )
                replace_operating_hours_sections(db, sections)
            except Exception:
                db.rollback()
                logger.warning("운영시간 크롤링 실패", exc_info=True)
                return CrawlResult(success=False, collected_count=0, message="운영시간 크롤링 실패")
        return CrawlResult(success=True, collected_count=len(sections))


def create_amusement_ride(db: Session, data: AmusementRideCreate) -> AmusementRide:
    ride = AmusementRide(**data.model_dump())
    db.add(ride)
    db.commit()
    db.refresh(ride)
    return ride


def list_amusement_rides(db: Session) -> list[AmusementRide]:
    return list(db.scalars(select(AmusementRide)).all())


def get_amusement_ride(db: Session, ride_id: int) -> AmusementRide | None:
    return db.get(AmusementRide, ride_id)


def update_amusement_ride(
    db: Session, ride: AmusementRide, data: AmusementRideUpdate
) -> AmusementRide:
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(ride, field, value)
    db.commit()
    db.refresh(ride)
    return ride


def delete_amusement_ride(db: Session, ride: AmusementRide) -> None:
    db.delete(ride)
    db.commit()
