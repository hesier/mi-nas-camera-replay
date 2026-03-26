from __future__ import annotations

from collections.abc import Generator
from pathlib import Path

from sqlalchemy import create_engine, inspect, text
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


def assert_sqlite_schema_compatible(engine: Engine) -> None:
    """
    显式校验 SQLite 现有库结构是否与当前代码版本兼容。

    由于 SQLite 缺少原生的迁移能力，且 SQLAlchemy 的 create_all() 不会修改既有表结构，
    如果用户沿用旧版 replay.db，会产生“表存在但缺列/主键不一致”的隐性错误。
    这里选择在启动与 CLI 入口提前失败，并给出明确的中文提示。
    """

    def _format_sqlite_recovery_hint() -> str:
        # sqlite_url 可配置，报错里不能硬编码 replay.db
        url = engine.url
        if url.get_backend_name() != "sqlite":
            return "请删除当前数据库文件后重试，或调整 sqlite_url 指向一个新库。"

        db_path = url.database
        if not db_path or db_path == ":memory:":
            return "请调整 sqlite_url 指向一个新库后重试。"

        name = Path(db_path).name
        return (
            f"请删除当前 SQLite 数据库文件（{name}）后重试，"
            "或调整 sqlite_url 指向一个新库。"
        )

    def _raise_incompatible(detail: str) -> None:
        raise RuntimeError(f"{detail}{_format_sqlite_recovery_hint()}")

    inspector = inspect(engine)
    table_names = set(inspector.get_table_names())

    # 新库或尚未建表：后续 create_all 会创建正确结构
    if not ({"video_files", "timeline_segments", "day_summaries"} & table_names):
        return

    if "video_files" in table_names:
        video_cols = {col["name"] for col in inspector.get_columns("video_files")}
        if "camera_no" not in video_cols:
            _raise_incompatible(
                "检测到旧版数据库结构：video_files 缺少 camera_no 列。该版本与当前程序不兼容。"
            )

    if "timeline_segments" in table_names:
        segment_cols = {
            col["name"] for col in inspector.get_columns("timeline_segments")
        }
        if "camera_no" not in segment_cols:
            _raise_incompatible(
                "检测到旧版数据库结构：timeline_segments 缺少 camera_no 列。该版本与当前程序不兼容。"
            )

    if "day_summaries" not in table_names:
        # 只要其它表已满足 camera_no 结构，day_summaries 不存在属于新库首次创建场景
        return

    columns = {col["name"] for col in inspector.get_columns("day_summaries")}
    pk_cols = inspector.get_pk_constraint("day_summaries").get(
        "constrained_columns"
    ) or []

    required = {"id", "camera_no", "day", "updated_at"}
    missing = required - columns
    if missing:
        missing_text = ",".join(sorted(missing))
        _raise_incompatible(
            "检测到数据库结构不兼容：day_summaries 缺少必要列（"
            f"{missing_text}）。"
        )

    # Task 2 的关键变化之一：day_summaries 必须以 id 作为主键。
    # 半升级旧库可能“补了 id 列”但仍保留 day 作为主键，这同样不兼容。
    if pk_cols != ["id"]:
        pk_text = ",".join(pk_cols) if pk_cols else "无"
        _raise_incompatible(
            "检测到数据库结构不兼容：day_summaries 主键必须为 id"
            f"（当前主键列：{pk_text}）。"
        )

    # 校验 (camera_no, day) 的唯一约束：不同 SQLAlchemy/SQLite 版本下反射行为可能不同，
    # 这里兜底用 PRAGMA index_* 做一次检查。
    uniques = inspector.get_unique_constraints("day_summaries")
    if any(set(u.get("column_names") or []) == {"camera_no", "day"} for u in uniques):
        return

    with engine.connect() as conn:
        index_rows = conn.execute(text("PRAGMA index_list('day_summaries')")).fetchall()
        for row in index_rows:
            # (seq, name, unique, origin, partial)
            index_name = row[1]
            is_unique = bool(row[2])
            if not is_unique:
                continue
            cols = conn.execute(text(f"PRAGMA index_info('{index_name}')")).fetchall()
            col_names = {c[2] for c in cols}  # (seqno, cid, name)
            if col_names == {"camera_no", "day"}:
                return

    _raise_incompatible(
        "检测到数据库结构不兼容：day_summaries 缺少 (camera_no, day) 的唯一约束。"
    )
