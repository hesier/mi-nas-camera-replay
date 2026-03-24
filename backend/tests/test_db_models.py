from sqlalchemy import text


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
        "file_path",
        "file_name",
        "file_size",
        "file_mtime",
        "name_start_at",
        "name_end_at",
        "probe_duration_sec",
        "actual_start_at",
        "actual_end_at",
        "time_source",
        "status",
        "issue_flags",
        "created_at",
        "updated_at",
    } <= table_columns["video_files"]

    assert {
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
