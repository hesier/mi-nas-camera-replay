import os
import subprocess
import sys
import sqlite3
from pathlib import Path

import pytest
from sqlalchemy import Integer, inspect, text


def test_create_all_tables(sqlite_session):
    tables = sqlite_session.execute(
        text("SELECT name FROM sqlite_master WHERE type='table'")
    ).fetchall()
    assert {"video_files", "timeline_segments", "day_summaries", "index_jobs"} <= {
        row[0] for row in tables
    }


def test_spec_columns_exist(sqlite_session):
    table_columns = {}
    for table in ("video_files", "timeline_segments", "day_summaries", "index_jobs"):
        columns = sqlite_session.execute(text(f"PRAGMA table_info('{table}')")).fetchall()
        table_columns[table] = {row[1] for row in columns}

    assert {
        "camera_no",
        "file_path",
        "file_name",
        "file_size",
        "file_mtime",
        "name_start_at",
        "name_end_at",
        "probe_duration_sec",
        "probe_video_codec",
        "probe_audio_codec",
        "probe_width",
        "probe_height",
        "probe_start_time_sec",
        "actual_start_at",
        "actual_end_at",
        "time_source",
        "status",
        "issue_flags",
        "created_at",
        "updated_at",
    } <= table_columns["video_files"]

    assert {
        "camera_no",
        "file_id",
        "day",
        "segment_start_at",
        "segment_end_at",
        "duration_sec",
        "playback_url",
        "file_offset_sec",
        "prev_gap_sec",
        "next_gap_sec",
        "status",
    } <= table_columns["timeline_segments"]

    assert {
        "id",
        "camera_no",
        "day",
        "first_segment_at",
        "last_segment_at",
        "total_segment_count",
        "total_recorded_sec",
        "total_gap_sec",
        "has_warning",
        "updated_at",
    } <= table_columns["day_summaries"]
    assert "preview_image_path" not in table_columns["day_summaries"]

    assert {
        "job_day",
        "status",
        "scanned_count",
        "success_count",
        "warning_count",
        "failed_count",
        "started_at",
        "finished_at",
    } <= table_columns["index_jobs"]


def test_video_file_mtime_is_integer(sqlite_session):
    inspector = inspect(sqlite_session.bind)
    columns = {col["name"]: col for col in inspector.get_columns("video_files")}
    assert isinstance(columns["file_mtime"]["type"], Integer)


def test_timeline_file_offset_has_schema_default_zero(sqlite_session):
    table_info = sqlite_session.execute(
        text("PRAGMA table_info('timeline_segments')")
    ).fetchall()
    file_offset_col = next(row for row in table_info if row[1] == "file_offset_sec")
    assert file_offset_col[4] in {"0", "0.0"}


def test_day_summary_id_is_primary_key(sqlite_session):
    inspector = inspect(sqlite_session.bind)
    pk = inspector.get_pk_constraint("day_summaries")
    assert pk["constrained_columns"] == ["id"]


def test_day_summaries_camera_day_is_unique(sqlite_session):
    inspector = inspect(sqlite_session.bind)
    uniques = inspector.get_unique_constraints("day_summaries")
    assert any(set(u.get("column_names") or []) == {"camera_no", "day"} for u in uniques)


def test_timeline_file_id_foreign_key_exists(sqlite_session):
    inspector = inspect(sqlite_session.bind)
    foreign_keys = inspector.get_foreign_keys("timeline_segments")
    assert any(
        fk["referred_table"] == "video_files"
        and fk["constrained_columns"] == ["file_id"]
        for fk in foreign_keys
    )


def test_import_db_without_video_root_env():
    backend_root = Path(__file__).resolve().parents[1]
    env = os.environ.copy()
    env.pop("VIDEO_ROOT", None)
    env["PYTHONPATH"] = str(backend_root)

    result = subprocess.run(
        [sys.executable, "-c", "import app.core.db"],
        env=env,
        cwd=backend_root,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr


def test_old_day_summaries_schema_raises_explicit_error(tmp_path):
    # 模拟旧版数据库：day_summaries(day TEXT PRIMARY KEY, ...)
    db_path = tmp_path / "replay.db"
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            "CREATE TABLE day_summaries (day TEXT PRIMARY KEY, updated_at TEXT NOT NULL)"
        )
        conn.commit()
    finally:
        conn.close()

    from sqlalchemy import create_engine

    from app.core.db import assert_sqlite_schema_compatible

    engine = create_engine(f"sqlite+pysqlite:///{db_path}", future=True)
    with pytest.raises(RuntimeError) as excinfo:
        assert_sqlite_schema_compatible(engine)

    # 错误信息必须明确提示删除 replay.db
    message = str(excinfo.value)
    assert "replay.db" in message
    assert "删除" in message
