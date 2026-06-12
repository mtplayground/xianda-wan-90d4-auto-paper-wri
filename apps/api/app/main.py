import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from http import HTTPStatus
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.exc import SQLAlchemyError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.auth.routes import router as auth_router
from app.compilations.routes import router as compilations_router
from app.config import get_settings
from app.db.session import get_session_factory, verify_database_connection
from app.papers.routes import router as papers_router
from app.references.routes import router as references_router
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


def _status_code_name(status_code: int) -> str:
    try:
        return HTTPStatus(status_code).phrase
    except ValueError:
        return "Error"


def _error_code(status_code: int) -> str:
    try:
        return HTTPStatus(status_code).name.lower()
    except ValueError:
        return "error"


def _json_error_response(
    *,
    status_code: int,
    message: str,
    code: str | None = None,
    details: list[dict[str, Any]] | None = None,
) -> JSONResponse:
    payload: dict[str, Any] = {
        "error": {
            "code": code or _error_code(status_code),
            "message": message,
        }
    }
    if details:
        payload["error"]["details"] = details
    return JSONResponse(status_code=status_code, content=payload)


def _validation_details(exc: RequestValidationError) -> list[dict[str, Any]]:
    details: list[dict[str, Any]] = []
    for error in exc.errors():
        location = error.get("loc", ())
        if isinstance(location, tuple | list):
            loc = ".".join(str(part) for part in location)
        else:
            loc = str(location)
        details.append(
            {
                "location": loc,
                "message": str(error.get("msg", "Invalid value")),
                "type": str(error.get("type", "value_error")),
            }
        )
    return details


@app.exception_handler(StarletteHTTPException)
async def http_error_handler(
    request: Request,
    exc: StarletteHTTPException,
) -> JSONResponse:
    del request
    detail = exc.detail
    message = detail if isinstance(detail, str) else _status_code_name(exc.status_code)
    return _json_error_response(status_code=exc.status_code, message=message)


@app.exception_handler(RequestValidationError)
async def validation_error_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    logger.info("Request validation failed for %s %s", request.method, request.url.path)
    return _json_error_response(
        status_code=422,
        code="validation_error",
        message="Request validation failed",
        details=_validation_details(exc),
    )


@app.exception_handler(Exception)
async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error(
        "Unhandled API error for %s %s",
        request.method,
        request.url.path,
        exc_info=(type(exc), exc, exc.__traceback__),
    )
    return _json_error_response(
        status_code=500,
        code="internal_server_error",
        message="Unexpected server error",
    )


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(compilations_router)
app.include_router(papers_router)
app.include_router(references_router)
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
