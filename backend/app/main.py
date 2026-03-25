from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.days import router as days_router
from app.api.index_jobs import router as index_jobs_router
from app.api.locate import router as locate_router
from app.api.timeline import router as timeline_router
from app.api.videos import router as videos_router
from app.core.config import get_settings
from app.core.db import Base, engine


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


def create_app() -> FastAPI:
    app = FastAPI(title="NAS Camera Replay", lifespan=lifespan)
    settings = get_settings()

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(days_router)
    app.include_router(timeline_router)
    app.include_router(locate_router)
    app.include_router(index_jobs_router)
    app.include_router(videos_router)
    return app


app = create_app()
