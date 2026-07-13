from pydantic import BaseModel, Field


class CrawlResult(BaseModel):
    """수동 크롤링 트리거 API의 공통 응답 스키마.

    congestion/operating_hours/weather 3개 job이 그대로 공유하고, catalog는 이를
    animals/plants/locations 3개 필드로 감싼 CatalogCrawlResult(catalog/schema.py)를
    별도로 쓴다.
    """

    success: bool = Field(description="이번 수집 성공 여부")
    collected_count: int = Field(description="이번 수집으로 저장/갱신된 건수")
    message: str | None = Field(
        default=None,
        description="실패 시 표시할 고정 메시지(서버 로그의 경고 메시지와 동일한 문자열). "
        "원본 예외 메시지를 그대로 노출하지 않는다 — 향후 예외 경로가 늘어나도 민감정보"
        "(외부 API 키가 포함된 URL 등)가 응답에 섞이지 않도록 하기 위함. 성공 시 null.",
    )
