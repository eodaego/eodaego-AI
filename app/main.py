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
from app.domains.catalog.router import router as catalog_router
from app.domains.crawling.router import congestion_router
from app.domains.crawling.router import router as crawling_router
from app.domains.facility.router import router as facility_router
from app.domains.prompt.router import router as prompt_router
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


app = FastAPI(title="eodaego-ai", lifespan=lifespan)
register_exception_handlers(app)
app.include_router(prompt_router)
app.include_router(crawling_router)
app.include_router(congestion_router)
app.include_router(catalog_router)
app.include_router(facility_router)
app.include_router(weather_router)


@app.get("/health")
def health_check() -> JSONResponse:
    try:
        with get_engine().connect() as connection:
            connection.execute(text("SELECT 1"))
    except Exception:
        return JSONResponse(status_code=503, content={"status": "error", "db": "error"})
    return JSONResponse(status_code=200, content={"status": "ok", "db": "ok"})
