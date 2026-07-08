from fastapi import FastAPI
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.core.errors import register_exception_handlers
from app.core.logging import configure_logging
from app.db.session import get_engine
from app.domains.crawling.router import router as crawling_router
from app.domains.prompt.router import router as prompt_router

configure_logging()

app = FastAPI(title="eodaego-ai")
register_exception_handlers(app)

app.include_router(crawling_router)
app.include_router(prompt_router)


@app.get("/health")
def health_check() -> JSONResponse:
    try:
        with get_engine().connect() as connection:
            connection.execute(text("SELECT 1"))
    except Exception:
        return JSONResponse(status_code=503, content={"status": "error", "db": "error"})
    return JSONResponse(status_code=200, content={"status": "ok", "db": "ok"})
