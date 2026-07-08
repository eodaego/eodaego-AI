from fastapi import FastAPI
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.core.errors import register_exception_handlers
from app.core.logging import configure_logging
from app.db.session import get_engine

configure_logging()

app = FastAPI(title="eodaego-ai")
register_exception_handlers(app)


@app.get("/health")
def health_check() -> JSONResponse:
    try:
        with get_engine().connect() as connection:
            connection.execute(text("SELECT 1"))
    except Exception:
        return JSONResponse(status_code=503, content={"status": "error", "db": "error"})
    return JSONResponse(status_code=200, content={"status": "ok", "db": "ok"})
