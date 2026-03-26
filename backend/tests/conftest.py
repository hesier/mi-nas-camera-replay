import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.db import Base
from app.models import DaySummary, IndexJob, TimelineSegment, VideoFile


def _import_models() -> None:
    # 显式引用模型模块，确保元数据注册到 Base
    _ = (VideoFile, TimelineSegment, DaySummary, IndexJob)


@pytest.fixture
def sqlite_session():
    _import_models()
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def existing_record():
    return VideoFile(
        camera_no=1,
        file_path="/videos/00_20260317000000_20260317001000.mp4",
        file_name="00_20260317000000_20260317001000.mp4",
        file_size=123,
        file_mtime=1711234567,
        name_start_at="2026-03-17T00:00:00+08:00",
        name_end_at="2026-03-17T00:10:00+08:00",
        probe_duration_sec=600.0,
        probe_video_codec=None,
        probe_audio_codec=None,
        probe_width=None,
        probe_height=None,
        probe_start_time_sec=0.0,
        actual_start_at="2026-03-17T00:00:00+08:00",
        actual_end_at="2026-03-17T00:10:00+08:00",
        time_source="filename",
        status="ready",
        issue_flags="[]",
        created_at="2026-03-24T00:00:00+08:00",
        updated_at="2026-03-24T00:00:00+08:00",
    )


@pytest.fixture
def incoming_file():
    return SimpleNamespace(
        path=Path("/videos/00_20260317000000_20260317001000.mp4"),
        name="00_20260317000000_20260317001000.mp4",
        file_size=123,
        file_mtime=1711234567,
    )


@pytest.fixture
def client(sqlite_session, monkeypatch, tmp_path):
    from fastapi.testclient import TestClient

    from app.core.db import get_db
    # Settings 现在要求：至少一个 VIDEO_ROOT_数字 + 非空 APP_PASSWORD
    monkeypatch.setenv("VIDEO_ROOT_1", str(tmp_path))
    monkeypatch.setenv("APP_PASSWORD", "test-password")

    import app.main as app_main

    # 避免 lifespan 中使用工作区真实 sqlite_url（例如 ./replay.db），确保测试完全 hermetic。
    monkeypatch.setattr(app_main, "get_engine", lambda: sqlite_session.get_bind())

    create_app = app_main.create_app

    app = create_app()

    def override_get_db():
        yield sqlite_session

    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()
