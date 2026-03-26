from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from app.core.config import get_settings

Base = declarative_base()


def _create_engine():
    settings = get_settings()
    return create_engine(settings.sqlite_url, future=True)

engine = None
SessionLocal = None


def _ensure_engine_initialized() -> None:
    """
    延迟初始化数据库引擎，避免在模块导入阶段就强依赖 Settings 的完整配置。
    """
    global engine, SessionLocal
    if engine is not None and SessionLocal is not None:
        return
    engine = _create_engine()
    SessionLocal = sessionmaker(
        bind=engine, autoflush=False, autocommit=False, future=True
    )


def get_engine():
    _ensure_engine_initialized()
    return engine


def get_db() -> Generator[Session, None, None]:
    _ensure_engine_initialized()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
