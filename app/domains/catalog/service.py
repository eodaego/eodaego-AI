import logging
import re
from typing import Any
from urllib.parse import parse_qs, urlencode, urlsplit

import requests
from bs4 import BeautifulSoup, Tag
from bs4.element import NavigableString
from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings
from app.db.session import get_engine
from app.domains.catalog.model import Animal, Plant

logger = logging.getLogger(__name__)

LIST_URL = "https://www.sisul.or.kr/open_content/childrenpark/bbs/bbsMsgList.do"
DETAIL_URL = "https://www.sisul.or.kr/open_content/childrenpark/bbs/bbsMsgDetail.do"
FILE_URL = "https://www.sisul.or.kr/open_content/bbs/bbsMsgFile.do"

ANIMAL_CATEGORY_MAP = {"01": "포유류", "02": "조류", "03": "파충류"}
PLANT_CATEGORY_MAP = {
    "01": "수목",
    "02": "관엽식물",
    "03": "다육식물",
    "04": "분재",
    "05": "야생화",
}
ANIMAL_LABEL_MAP = {
    "학명": "scientific_name",
    "영명": "english_name",
    "분류": "classification",
    "분포": "distribution",
    "먹는것": "diet",
}


def _extract_query_param(href: str, key: str) -> str | None:
    values = parse_qs(urlsplit(href).query).get(key)
    return values[0] if values else None


def _build_thumbnail_url(img_src: str, bcd: str) -> str | None:
    query = parse_qs(urlsplit(img_src).query)
    filenm = query.get("filenm", [None])[0]
    year = query.get("year", [None])[0]
    if filenm is None or year is None:
        return None
    params = {"bcd": bcd, "filenm": filenm, "year": year, "size": "small"}
    return f"{FILE_URL}?{urlencode(params)}"


def _total_page_count(soup: BeautifulSoup) -> int:
    match = re.search(r"현재페이지\s*\d+\s*/\s*(\d+)\s*page", soup.get_text())
    return int(match.group(1)) if match else 1


def _parse_labeled_fields(p_tag: Tag, label_map: dict[str, str]) -> dict[str, str]:
    fields: dict[str, str] = {}
    current_key: str | None = None
    for child in p_tag.children:
        if isinstance(child, Tag) and child.name == "span":
            current_key = label_map.get(child.get_text(strip=True))
            continue
        if type(child) is NavigableString and current_key is not None:
            value = str(child).strip()
            if value.startswith(":"):
                value = value[1:].strip()
            if value:
                fields[current_key] = value
                current_key = None
    return fields


def _fetch_list_page(bcd: str, category_code: str, page_no: int) -> BeautifulSoup:
    params: dict[str, str | int] = {"cate1": category_code, "bcd": bcd, "pgno": page_no}
    response = requests.get(LIST_URL, params=params, timeout=10)
    response.raise_for_status()
    return BeautifulSoup(response.text, "lxml")


def _parse_animal_items(
    soup: BeautifulSoup, category_code: str, category_name: str
) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for li in soup.select("div.list > ul > li"):
        name_link = li.select_one("div > p a")
        if name_link is None or not name_link.get("href"):
            continue
        msg_seq_str = _extract_query_param(str(name_link["href"]), "msg_seq")
        if msg_seq_str is None:
            continue
        msg_seq = int(msg_seq_str)
        img = li.select_one("p.photo img")
        margin_p = li.select_one("p.margin_b20")
        date_p = li.select_one("p.date")
        fields = _parse_labeled_fields(margin_p, ANIMAL_LABEL_MAP) if margin_p else {}
        registered_date = date_p.get_text(strip=True).split("/")[0].strip() if date_p else None
        items.append(
            {
                "msg_seq": msg_seq,
                "category": category_name,
                "name": name_link.get_text(strip=True),
                "thumbnail_url": (
                    _build_thumbnail_url(str(img["src"]), "animal")
                    if img and img.get("src")
                    else None
                ),
                "registered_date": registered_date,
                "scientific_name": fields.get("scientific_name"),
                "english_name": fields.get("english_name"),
                "classification": fields.get("classification"),
                "distribution": fields.get("distribution"),
                "diet": fields.get("diet"),
                "source_url": f"{DETAIL_URL}?msg_seq={msg_seq}&cate1={category_code}&bcd=animal",
            }
        )
    return items


def _parse_plant_items(
    soup: BeautifulSoup, category_code: str, category_name: str
) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for li in soup.select("div.list > ul > li"):
        name_link = li.select_one("div > p a")
        if name_link is None or not name_link.get("href"):
            continue
        msg_seq_str = _extract_query_param(str(name_link["href"]), "msg_seq")
        if msg_seq_str is None:
            continue
        msg_seq = int(msg_seq_str)
        img = li.select_one("p.photo img")
        date_p = li.select_one("p.date")
        description_p = li.select_one("div > p:nth-of-type(2)")
        description = None
        if description_p is not None:
            description = description_p.get_text(strip=True).removeprefix("■ 특징").strip()
        registered_date = date_p.get_text(strip=True).split("/")[0].strip() if date_p else None
        items.append(
            {
                "msg_seq": msg_seq,
                "category": category_name,
                "name": name_link.get_text(strip=True),
                "thumbnail_url": (
                    _build_thumbnail_url(str(img["src"]), "plant")
                    if img and img.get("src")
                    else None
                ),
                "registered_date": registered_date,
                "description": description,
                "source_url": f"{DETAIL_URL}?msg_seq={msg_seq}&cate1={category_code}&bcd=plant",
            }
        )
    return items


def crawl_all_animals() -> list[dict[str, Any]]:
    all_items: list[dict[str, Any]] = []
    for category_code, category_name in ANIMAL_CATEGORY_MAP.items():
        page_no = 1
        while True:
            soup = _fetch_list_page("animal", category_code, page_no)
            items = _parse_animal_items(soup, category_code, category_name)
            if not items:
                break
            all_items.extend(items)
            if page_no >= _total_page_count(soup):
                break
            page_no += 1
    return all_items


def crawl_all_plants() -> list[dict[str, Any]]:
    all_items: list[dict[str, Any]] = []
    for category_code, category_name in PLANT_CATEGORY_MAP.items():
        page_no = 1
        while True:
            soup = _fetch_list_page("plant", category_code, page_no)
            items = _parse_plant_items(soup, category_code, category_name)
            if not items:
                break
            all_items.extend(items)
            if page_no >= _total_page_count(soup):
                break
            page_no += 1
    return all_items


def upsert_animals(db: Session, items: list[dict[str, Any]]) -> None:
    for item in items:
        existing = db.scalar(select(Animal).where(Animal.msg_seq == item["msg_seq"]))
        if existing is None:
            db.add(Animal(**item))
        else:
            for field, value in item.items():
                setattr(existing, field, value)
    db.commit()


def upsert_plants(db: Session, items: list[dict[str, Any]]) -> None:
    for item in items:
        existing = db.scalar(select(Plant).where(Plant.msg_seq == item["msg_seq"]))
        if existing is None:
            db.add(Plant(**item))
        else:
            for field, value in item.items():
                setattr(existing, field, value)
    db.commit()


def list_animals(db: Session) -> list[Animal]:
    return list(db.scalars(select(Animal)).all())


def list_plants(db: Session) -> list[Plant]:
    return list(db.scalars(select(Plant)).all())


ANIMAL_LOCATION_URL = "https://apis.data.go.kr/B553774/AnmalLocation"


def sync_animal_locations(db: Session) -> None:
    settings = get_settings()
    params: dict[str, str | int] = {
        "serviceKey": settings.data_go_kr_service_key,
        "pageNo": 1,
        "numOfRows": 100,
        "type": "json",
    }
    try:
        response = requests.get(ANIMAL_LOCATION_URL, params=params, timeout=10)
        response.raise_for_status()
    except requests.RequestException as exc:
        status = getattr(exc.response, "status_code", "unknown")
        raise RuntimeError(f"동물 위치 정보 API 호출 실패 (status={status})") from None
    body = response.json().get("body", {})
    raw_items = body.get("items", {}).get("item", [])
    entries = raw_items if isinstance(raw_items, list) else [raw_items]
    for entry in entries:
        animal_name = entry.get("kordesc")
        location_name = entry.get("lname")
        if not animal_name or not location_name:
            continue
        normalized = animal_name.replace(" ", "")
        animal = db.scalar(select(Animal).where(func.replace(Animal.name, " ", "") == normalized))
        if animal is not None:
            animal.location_name = location_name
    db.commit()


def crawl_catalog_job() -> None:
    session_factory = sessionmaker(bind=get_engine())
    with session_factory() as db:
        try:
            upsert_animals(db, crawl_all_animals())
        except Exception:
            db.rollback()
            logger.warning("동물 도감 크롤링 실패", exc_info=True)
        try:
            upsert_plants(db, crawl_all_plants())
        except Exception:
            db.rollback()
            logger.warning("식물 도감 크롤링 실패", exc_info=True)
        try:
            sync_animal_locations(db)
        except Exception:
            db.rollback()
            logger.warning("동물 위치 정보 동기화 실패", exc_info=True)
