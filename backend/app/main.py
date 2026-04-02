from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.auth import router as auth_router
from app.api.cameras import router as cameras_router
from app.api.days import router as days_router
from app.api.index_jobs import router as index_jobs_router
from app.api.locate import router as locate_router
from app.api.timeline import router as timeline_router
from app.api.videos import router as videos_router
from app.core.config import Settings, get_settings
from app.core.db import Base, assert_sqlite_schema_compatible, get_engine
from app.tasks.index_scheduler import start_index_scheduler, stop_index_scheduler
from app.tasks.index_videos import enqueue_index_job


def trigger_startup_index(*, settings: Settings | None = None):
    current_settings = settings or get_settings()
    if not current_settings.index_on_startup:
        return None
    return enqueue_index_job(camera_roots=current_settings.camera_roots)


def get_frontend_dist_dir() -> Path:
    return Path(__file__).resolve().parent / "static"


def configure_frontend(app: FastAPI) -> None:
    frontend_dist_dir = get_frontend_dist_dir()
    index_file = frontend_dist_dir / "index.html"
    if not index_file.is_file():
        return

    assets_dir = frontend_dist_dir / "assets"
    if assets_dir.is_dir():
        app.mount("/assets", StaticFiles(directory=assets_dir), name="frontend-assets")

    @app.get("/", include_in_schema=False)
    def serve_frontend_index():
        return FileResponse(index_file)

    @app.get("/{full_path:path}", include_in_schema=False)
    def serve_frontend_route(full_path: str):
        if full_path.startswith("api/"):
            raise HTTPException(status_code=404, detail="Not Found")

        requested_path = (frontend_dist_dir / full_path).resolve()
        if frontend_dist_dir.resolve() not in requested_path.parents:
            raise HTTPException(status_code=404, detail="Not Found")

        if requested_path.is_file():
            return FileResponse(requested_path)

        return FileResponse(index_file)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    engine = get_engine()
    assert_sqlite_schema_compatible(engine)
    Base.metadata.create_all(bind=engine)
    startup_index_job = trigger_startup_index(settings=settings)
    scheduler = start_index_scheduler(settings=settings)
    app.state.startup_index_job = startup_index_job
    app.state.index_scheduler = scheduler
    try:
        yield
    finally:
        stop_index_scheduler(scheduler)


def create_app() -> FastAPI:
    app = FastAPI(title="Xiaomi NAS Camera Replay", lifespan=lifespan)
    settings = get_settings()

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(auth_router)
    app.include_router(days_router)
    app.include_router(cameras_router)
    app.include_router(timeline_router)
    app.include_router(locate_router)
    app.include_router(index_jobs_router)
    app.include_router(videos_router)
    configure_frontend(app)
    return app


app = create_app()
