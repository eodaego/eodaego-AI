import logging
from datetime import date, datetime
from typing import Any

import requests
from sqlalchemy import delete, select
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings
from app.core.job_lock import JobRunGuard
from app.core.schema import CrawlResult
from app.db.session import get_engine
from app.domains.event.model import CulturalEvent

logger = logging.getLogger(__name__)

CULTURAL_EVENT_BASE_URL = "http://openapi.seoul.go.kr:8088"
EVENT_PLACE_KEYWORD = "어린이대공원"
_PAGE_SIZE = 1000


def _fetch_page(start: int, end: int) -> list[dict[str, Any]]:
    settings = get_settings()
    url = (
        f"{CULTURAL_EVENT_BASE_URL}/{settings.seoul_open_api_key}/json/"
        f"culturalEventInfo/{start}/{end}"
    )
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
    except requests.RequestException as exc:
        status = getattr(exc.response, "status_code", "unknown")
        raise RuntimeError(f"서울시 문화행사 API 호출 실패 (status={status})") from None
    body = response.json().get("culturalEventInfo", {})
    rows = body.get("row", [])
    return rows if isinstance(rows, list) else [rows]


def fetch_all_cultural_events() -> list[dict[str, Any]]:
    """서울시 전체 문화행사를 페이지네이션으로 끝까지 조회한다.

    이 API는 장소 필터 파라미터가 없어 전체 목록을 받아온 뒤 클라이언트에서
    걸러야 한다."""
    all_rows: list[dict[str, Any]] = []
    start = 1
    while True:
        end = start + _PAGE_SIZE - 1
        rows = _fetch_page(start, end)
        if not rows:
            break
        all_rows.extend(rows)
        if len(rows) < _PAGE_SIZE:
            break
        start += _PAGE_SIZE
    return all_rows


def _parse_date(value: str) -> date:
    """STRTDATE/END_DATE는 'YYYY-MM-DD HH:MM:SS.f' 형식으로 오므로 날짜 부분만 취한다
    (실제 API 응답으로 확인함, 시각 부분은 사용하지 않는다)."""
    date_part = value.split(" ")[0]
    return datetime.strptime(date_part, "%Y-%m-%d").date()


def filter_and_parse_children_park_events(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """PLACE에 '어린이대공원'이 포함된 행만 골라 CulturalEvent 필드로 매핑한다.

    PROGRAM/ETC_DESC/USE_TRGT/USE_FEE/ORG_LINK/HMPG_ADDR은 값이 없을 때 필드 자체가
    생략되지 않고 빈 문자열로 오므로, 저장 전 None으로 정규화한다(실제 API 응답으로 확인함)."""
    items: list[dict[str, Any]] = []
    for row in rows:
        place = row.get("PLACE", "")
        if EVENT_PLACE_KEYWORD not in place:
            continue
        items.append(
            {
                "title": row["TITLE"],
                "place": place,
                "start_date": _parse_date(row["STRTDATE"]),
                "end_date": _parse_date(row["END_DATE"]),
                "description": row.get("PROGRAM") or row.get("ETC_DESC") or None,
                "target": row.get("USE_TRGT") or None,
                "fee": row.get("USE_FEE") or None,
                "homepage_url": row.get("ORG_LINK") or row.get("HMPG_ADDR") or None,
            }
        )
    return items


def sync_cultural_events(db: Session, items: list[dict[str, Any]]) -> int:
    """cultural_event 테이블을 이번 크롤링 결과로 전체 교체한다(삭제 후 재삽입).

    서울시 API가 안정적인 고유 ID를 제공하지 않아 upsert 대신 전체 교체 방식을
    쓴다 — 이 테이블은 항상 '현재 유효한 행사 목록'만 담는다."""
    db.execute(delete(CulturalEvent))
    for item in items:
        db.add(CulturalEvent(**item))
    db.commit()
    return len(items)


def list_cultural_events(db: Session) -> list[CulturalEvent]:
    stmt = select(CulturalEvent).order_by(CulturalEvent.start_date)
    return list(db.scalars(stmt).all())


def crawl_event_job() -> CrawlResult:
    with JobRunGuard("crawl_event"):
        session_factory = sessionmaker(bind=get_engine())
        with session_factory() as db:
            try:
                rows = fetch_all_cultural_events()
                items = filter_and_parse_children_park_events(rows)
                count = sync_cultural_events(db, items)
            except Exception:
                db.rollback()
                logger.warning("행사 데이터 크롤링 실패", exc_info=True)
                return CrawlResult(
                    success=False, collected_count=0, message="행사 데이터 크롤링 실패"
                )
        return CrawlResult(success=True, collected_count=count)
