from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.orm import sessionmaker

from app.core.errors import register_exception_handlers
from app.core.logging import configure_logging
from app.db.session import get_engine
from app.domains.ai.router import router as ai_router
from app.domains.catalog.router import router as catalog_router
from app.domains.crawling.router import congestion_router
from app.domains.crawling.router import router as crawling_router
from app.domains.event.router import router as event_router
from app.domains.facility.router import router as facility_router
from app.domains.prompt.router import router as prompt_router
from app.domains.recommendation.router import router as recommendation_router
from app.domains.weather.router import router as weather_router
from app.scheduler.registry import JOB_REGISTRY, bootstrap_scheduler

configure_logging()

scheduler = BackgroundScheduler()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    session_factory = sessionmaker(bind=get_engine())
    with session_factory() as db:
        bootstrap_scheduler(scheduler, db, JOB_REGISTRY)
    scheduler.start()
    yield
    scheduler.shutdown(wait=False)


app = FastAPI(
    title="eodaego-ai",
    description=(
        "서울어린이대공원 방문객 대상 AI 코스 추천·도감 수집 서비스 **어대GO**의 내부 전용 AI 백엔드입니다.\n\n"  # noqa: E501
        "- `eodaego-server`(BE, Spring Boot)만 내부 브리지 네트워크(`eodaego-internal`)를 통해 "
        "컨테이너 이름으로 호출하며, FE(Flutter)나 관리자 브라우저에서 직접 호출되지 않습니다.\n"
        "- `/health`를 제외한 모든 엔드포인트는 `X-Internal-Api-Key` 헤더 인증이 필요합니다.\n"
        "- 성공 응답은 각 엔드포인트의 응답 스키마를 그대로 반환합니다(별도 envelope 없음). "
        '에러 응답만 `{"success": false, "data": null, "error": {"code": ..., "message": ...}}` '
        "형태의 공통 envelope으로 통일됩니다(전역 예외 핸들러)."
    ),
    version="0.1.0",
    openapi_tags=[
        {
            "name": "ai",
            "description": "SUH-AIder(개인 LLM 서버) 연동 기반 관리자 제어형 AI 챗 응답 생성",
        },
        {
            "name": "prompts",
            "description": "AI 챗 응답 생성에 사용되는 프롬프트 템플릿 CRUD (BE 관리자 SSR 페이지가 호출)",  # noqa: E501
        },
        {
            "name": "recommendation",
            "description": "선호 태그·체류 시간 등 사용자 입력만으로 Facility·날씨·혼잡도를 "
            "조합해 추천 동선을 생성 (개인 LLM 서버 호출)",
        },
        {
            "name": "crawling",
            "description": "크롤링 작업 실행 스케줄 설정 CRUD (DB에는 즉시 반영되지만, "
            "실제 스케줄러 등록은 AI 서버 재시작 시점에만 이루어짐)",
        },
        {
            "name": "congestion",
            "description": "서울시 실시간 도시데이터 기반 어린이대공원 혼잡도 스냅샷 조회 (조회 전용)",  # noqa: E501
        },
        {
            "name": "catalog",
            "description": "동식물 도감 데이터 조회 (조회 전용, 수집은 crawl_catalog 스케줄 job이 담당)",  # noqa: E501
        },
        {
            "name": "facility",
            "description": "시설·운영시간 정보 조회 및 놀이기구 관리자 CRUD",
        },
        {
            "name": "weather",
            "description": "기상청 API 기반 어린이대공원 날씨 스냅샷 조회 (조회 전용)",
        },
        {
            "name": "event",
            "description": "서울 열린데이터광장 공공API 기반 어린이대공원 행사·공연 정보 조회 "
            "(조회 전용, 수집은 crawl_event 스케줄 job이 담당)",
        },
    ],
    lifespan=lifespan,
)
register_exception_handlers(app)
app.include_router(ai_router)
app.include_router(prompt_router)
app.include_router(recommendation_router)
app.include_router(crawling_router)
app.include_router(congestion_router)
app.include_router(catalog_router)
app.include_router(facility_router)
app.include_router(weather_router)
app.include_router(event_router)


@app.get("/health")
def health_check() -> JSONResponse:
    try:
        with get_engine().connect() as connection:
            connection.execute(text("SELECT 1"))
    except Exception:
        return JSONResponse(status_code=503, content={"status": "error", "db": "error"})
    return JSONResponse(status_code=200, content={"status": "ok", "db": "ok"})
