from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.config import get_settings


settings = get_settings()
app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health_check() -> dict[str, str]:
    return {"status": "ok", "service": settings.app_name}


WEB_DIST = Path(__file__).resolve().parents[2] / "web" / "dist"

if WEB_DIST.exists():
    app.mount("/assets", StaticFiles(directory=WEB_DIST / "assets"), name="assets")


@app.get("/{path:path}", include_in_schema=False)
def serve_spa(path: str) -> FileResponse:
    index_file = WEB_DIST / "index.html"
    if not index_file.exists():
        return FileResponse(Path(__file__).resolve().parent / "static" / "index.html")
    return FileResponse(index_file)
