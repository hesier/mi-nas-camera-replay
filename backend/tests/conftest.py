import os
import sys
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("VIDEO_ROOT", "./videos")

from app.core.db import Base
from app.models import DaySummary, IndexJob, TimelineSegment, VideoFile


def _import_models() -> None:
    # 显式引用模型模块，确保元数据注册到 Base
    _ = (VideoFile, TimelineSegment, DaySummary, IndexJob)


@pytest.fixture
def sqlite_session():
    _import_models()
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
