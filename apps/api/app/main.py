import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.exc import SQLAlchemyError

from app.auth.routes import router as auth_router
from app.config import get_settings
from app.db.session import get_session_factory, verify_database_connection
from app.papers.routes import router as papers_router
from app.storage.client import get_storage_client
from app.templates.builtins import seed_builtin_templates
from app.templates.routes import router as templates_router

settings = get_settings()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    storage = get_storage_client()
    try:
        with get_session_factory()() as session:
            seed_builtin_templates(session, storage)
    except Exception:
        logger.exception("Built-in template seeding failed")
        raise
    yield


app = FastAPI(title=settings.app_name, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(papers_router)
app.include_router(templates_router)


@app.get("/api/health")
def health_check() -> dict[str, str]:
    return {"status": "ok", "service": settings.app_name}


@app.get("/api/ready")
def readiness_check() -> dict[str, str]:
    try:
        verify_database_connection()
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except SQLAlchemyError as exc:
        logger.exception("Database readiness check failed")
        raise HTTPException(status_code=503, detail="database unavailable") from exc
    return {"status": "ok", "database": "connected"}


WEB_DIST = Path(__file__).resolve().parents[2] / "web" / "dist"

if WEB_DIST.exists():
    app.mount("/assets", StaticFiles(directory=WEB_DIST / "assets"), name="assets")


@app.get("/{path:path}", include_in_schema=False)
def serve_spa(path: str) -> FileResponse:
    index_file = WEB_DIST / "index.html"
    if not index_file.exists():
        return FileResponse(Path(__file__).resolve().parent / "static" / "index.html")
    return FileResponse(index_file)
