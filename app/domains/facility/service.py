import logging
from typing import Any

import requests
from bs4 import BeautifulSoup
from sqlalchemy import delete, select
from sqlalchemy.orm import Session, sessionmaker

from app.db.session import get_engine
from app.domains.facility.model import Facility, OperatingHoursSection

logger = logging.getLogger(__name__)

USE_JSP_URL = "https://www.sisul.or.kr/open_content/childrenpark/introduce/use.jsp"


def list_facilities(db: Session) -> list[Facility]:
    return list(db.scalars(select(Facility)).all())


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


def crawl_operating_hours_job() -> None:
    session_factory = sessionmaker(bind=get_engine())
    with session_factory() as db:
        try:
            replace_operating_hours_sections(db, crawl_operating_hours())
        except Exception:
            logger.warning("운영시간 크롤링 실패", exc_info=True)
