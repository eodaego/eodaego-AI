"""서울어린이대공원 시설물 위치정보 xlsx 1회성 임포트 스크립트.

실행: uv run python scripts/import_facility_locations.py
매번 재실행해도 external_id 기준으로 중복 없이 upsert된다.
"""

import openpyxl
from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

from app.db.session import get_engine
from app.domains.facility.model import Facility

XLSX_PATH = "data/seoul_childrens_grand_park_facility_locations.xlsx"
SHEET_NAME = "위치정보 작성"


def main() -> None:
    workbook = openpyxl.load_workbook(XLSX_PATH, data_only=True)
    sheet = workbook[SHEET_NAME]
    session_factory = sessionmaker(bind=get_engine())
    imported = 0
    with session_factory() as db:
        for row in sheet.iter_rows(min_row=2, values_only=True):
            external_id, category, name, intro, description, latitude, longitude, facility_type = (
                row
            )
            if external_id is None or name is None:
                continue
            existing = db.scalar(select(Facility).where(Facility.external_id == int(external_id)))
            values = {
                "category": str(category),
                "name": str(name),
                "intro": intro,
                "description": description,
                "latitude": float(latitude) if latitude is not None else None,
                "longitude": float(longitude) if longitude is not None else None,
                "facility_type": facility_type,
            }
            if existing is None:
                db.add(Facility(external_id=int(external_id), **values))
            else:
                for field, value in values.items():
                    setattr(existing, field, value)
            imported += 1
        db.commit()
    print(f"시설물 위치정보 임포트 완료: {imported}건")


if __name__ == "__main__":
    main()
