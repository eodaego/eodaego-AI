from datetime import datetime
from typing import Annotated
from zoneinfo import ZoneInfo

from pydantic import AfterValidator, PlainSerializer

KST = ZoneInfo("Asia/Seoul")


def to_kst(dt: datetime) -> datetime:
    """naive datetime은 KST 벽시계 값으로 간주해 tzinfo만 부착하고,
    aware datetime은 어떤 timezone이든 무조건 KST로 변환한다."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=KST)
    return dt.astimezone(KST)


def format_kst(dt: datetime) -> str:
    """KST 기준 'yyyy-MM-ddTHH:mm:ss' 문자열로 변환한다(오프셋·마이크로초 없음)."""
    return to_kst(dt).strftime("%Y-%m-%dT%H:%M:%S")


KstDatetime = Annotated[
    datetime, AfterValidator(to_kst), PlainSerializer(format_kst, return_type=str)
]
