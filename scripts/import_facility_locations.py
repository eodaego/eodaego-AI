"""서울어린이대공원 시설물 위치정보 xlsx 임포트 CLI.

실행: uv run python -m scripts.import_facility_locations
매번 재실행해도 external_id 기준으로 중복 없이 upsert된다. 같은 로직은
POST /api/v1/facility/import API로도 호출할 수 있다(app/domains/facility/service.py의
import_facility_locations 함수를 두 경로가 함께 사용한다).
"""

from sqlalchemy.orm import sessionmaker

from app.db.session import get_engine
from app.domains.facility.service import import_facility_locations


def main() -> None:
    session_factory = sessionmaker(bind=get_engine())
    with session_factory() as db:
        result = import_facility_locations(db)
    if result.success:
        print(f"시설물 위치정보 임포트 완료: {result.collected_count}건")
    else:
        print(f"시설물 위치정보 임포트 실패: {result.message}")


if __name__ == "__main__":
    main()
