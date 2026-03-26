from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from app.core.config import get_settings

Base = declarative_base()

_engine: Engine | None = None
_session_maker: sessionmaker | None = None


def get_engine() -> Engine:
    """
    延迟初始化数据库引擎，避免在模块导入阶段就强依赖 Settings 的必填配置。

    注意：应用真正启动时仍然需要完整配置；这里只是去掉“导入即执行”的耦合。
    """
    global _engine, _session_maker
    if _engine is None or _session_maker is None:
        settings = get_settings()
        _engine = create_engine(settings.sqlite_url, future=True)
        _session_maker = sessionmaker(
            bind=_engine,
            autoflush=False,
            autocommit=False,
            future=True,
        )
    return _engine


def SessionLocal() -> Session:
    """
    兼容旧用法：SessionLocal() -> Session。

    这里保持 SessionLocal 可调用，供 index_scheduler/index_videos 的默认参数直接引用。
    """
    global _session_maker
    if _session_maker is None:
        get_engine()
    assert _session_maker is not None
    return _session_maker()


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

