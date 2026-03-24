from __future__ import annotations

import json
from pathlib import Path

from app.models import DaySummary, IndexJob, TimelineSegment, VideoFile
from app.services.media_probe import ProbeResult
from app.tasks.index_videos import run_index_job


def test_run_index_job_persists_job_and_day_summary(
    sqlite_session,
    monkeypatch,
    tmp_path,
):
    file_name = "00_20260317000000_20260317001000.mp4"
    file_path = tmp_path / file_name
    file_path.write_bytes(b"x")

    monkeypatch.setattr(
        "app.tasks.index_videos.scan_video_files",
        lambda _: [
            type(
                "ScannedVideoFile",
                (),
                {
                    "path": file_path,
                    "name": file_name,
                    "file_size": 1,
                    "file_mtime": 1711209600,
                },
            )()
        ],
    )
    monkeypatch.setattr(
        "app.tasks.index_videos.probe_media",
        lambda _: ProbeResult(duration_sec=600.0, start_time_sec=0.0),
    )

    job = run_index_job(sqlite_session, root=tmp_path)

    stored_job = sqlite_session.get(IndexJob, job.id)
    assert stored_job is not None
    assert stored_job.job_day == "all"
    assert stored_job.status == "success"
    assert stored_job.scanned_count == 1
    assert stored_job.success_count == 1
    assert stored_job.warning_count == 0
    assert stored_job.failed_count == 0
    assert stored_job.finished_at is not None

    stored_file = sqlite_session.query(VideoFile).one()
    assert stored_file.file_path == str(file_path)
    assert stored_file.actual_end_at == "2026-03-17T00:10:00+08:00"

    stored_segments = sqlite_session.query(TimelineSegment).all()
    assert len(stored_segments) == 1
    assert stored_segments[0].day == "2026-03-17"
    assert stored_segments[0].playback_url == f"/api/videos/{stored_file.id}/stream"

    summary = sqlite_session.get(DaySummary, "2026-03-17")
    assert summary is not None
    assert summary.total_segment_count == 1
    assert summary.total_recorded_sec == 600.0
    assert summary.total_gap_sec == 0.0
    assert summary.has_warning is False


def test_run_index_job_skips_reprobe_when_file_unchanged(
    sqlite_session,
    monkeypatch,
    tmp_path,
):
    file_name = "00_20260317000000_20260317001000.mp4"
    file_path = tmp_path / file_name
    file_path.write_bytes(b"x")
    sqlite_session.add(
        VideoFile(
            file_path=str(file_path),
            file_name=file_name,
            file_size=1,
            file_mtime=1711209600,
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
    )
    sqlite_session.commit()

    monkeypatch.setattr(
        "app.tasks.index_videos.scan_video_files",
        lambda _: [
            type(
                "ScannedVideoFile",
                (),
                {
                    "path": file_path,
                    "name": file_name,
                    "file_size": 1,
                    "file_mtime": 1711209600,
                },
            )()
        ],
    )

    probe_called = False

    def fake_probe(_: Path):
        nonlocal probe_called
        probe_called = True
        return ProbeResult(duration_sec=600.0, start_time_sec=0.0)

    monkeypatch.setattr("app.tasks.index_videos.probe_media", fake_probe)

    job = run_index_job(sqlite_session, root=tmp_path)

    assert probe_called is False
    assert job.scanned_count == 1
    assert job.success_count == 1
    assert job.failed_count == 0


def test_run_index_job_target_day_rebuilds_unchanged_stale_timeline(
    sqlite_session,
    monkeypatch,
    tmp_path,
):
    file_name = "00_20260317000000_20260317001000.mp4"
    file_path = tmp_path / file_name
    file_path.write_bytes(b"x")

    sqlite_session.add(
        VideoFile(
            file_path=str(file_path),
            file_name=file_name,
            file_size=1,
            file_mtime=1711209600,
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
    )
    sqlite_session.commit()
    existing = sqlite_session.query(VideoFile).one()
    sqlite_session.add(
        TimelineSegment(
            file_id=existing.id,
            day="2026-03-17",
            segment_start_at="2026-03-17T00:01:00+08:00",
            segment_end_at="2026-03-17T00:02:00+08:00",
            duration_sec=60.0,
            playback_url="/stale/url",
            file_offset_sec=0.0,
            prev_gap_sec=None,
            next_gap_sec=None,
            status="warning",
        )
    )
    sqlite_session.add(
        DaySummary(
            day="2026-03-17",
            first_segment_at="2026-03-17T00:01:00+08:00",
            last_segment_at="2026-03-17T00:02:00+08:00",
            total_segment_count=99,
            total_recorded_sec=60.0,
            total_gap_sec=12.0,
            has_warning=True,
            updated_at="2026-03-24T00:00:00+08:00",
        )
    )
    sqlite_session.commit()

    monkeypatch.setattr(
        "app.tasks.index_videos.scan_video_files",
        lambda _: [
            type(
                "ScannedVideoFile",
                (),
                {
                    "path": file_path,
                    "name": file_name,
                    "file_size": 1,
                    "file_mtime": 1711209600,
                },
            )()
        ],
    )
    monkeypatch.setattr(
        "app.tasks.index_videos.probe_media",
        lambda _: (_ for _ in ()).throw(AssertionError("不应重新探测未变化文件")),
    )

    job = run_index_job(sqlite_session, root=tmp_path, target_day="2026-03-17")

    assert job.scanned_count == 1
    assert job.success_count == 1
    assert job.failed_count == 0

    rebuilt_segments = sqlite_session.query(TimelineSegment).all()
    assert len(rebuilt_segments) == 1
    assert rebuilt_segments[0].segment_start_at == "2026-03-17T00:00:00+08:00"
    assert rebuilt_segments[0].segment_end_at == "2026-03-17T00:10:00+08:00"
    assert rebuilt_segments[0].playback_url == f"/api/videos/{existing.id}/stream"

    summary = sqlite_session.get(DaySummary, "2026-03-17")
    assert summary is not None
    assert summary.total_segment_count == 1
    assert summary.total_recorded_sec == 600.0
    assert summary.total_gap_sec == 0.0
    assert summary.has_warning is False


def test_run_index_job_persists_invalid_video_file_when_probe_fails(
    sqlite_session,
    monkeypatch,
    tmp_path,
):
    file_name = "00_20260317000000_20260317001000.mp4"
    file_path = tmp_path / file_name
    file_path.write_bytes(b"x")

    monkeypatch.setattr(
        "app.tasks.index_videos.scan_video_files",
        lambda _: [
            type(
                "ScannedVideoFile",
                (),
                {
                    "path": file_path,
                    "name": file_name,
                    "file_size": 1,
                    "file_mtime": 1711209600,
                },
            )()
        ],
    )
    monkeypatch.setattr(
        "app.tasks.index_videos.probe_media",
        lambda _: (_ for _ in ()).throw(ValueError("ffprobe execution failed")),
    )

    job = run_index_job(sqlite_session, root=tmp_path)

    assert job.scanned_count == 1
    assert job.success_count == 0
    assert job.failed_count == 1
    assert job.status == "warning"

    stored_file = sqlite_session.query(VideoFile).one()
    assert stored_file.file_path == str(file_path)
    assert stored_file.status == "invalid"
    assert json.loads(stored_file.issue_flags) == ["invalid_media"]
    assert stored_file.name_start_at == "2026-03-17T00:00:00+08:00"
    assert stored_file.name_end_at == "2026-03-17T00:10:00+08:00"

    assert sqlite_session.query(TimelineSegment).count() == 0
    assert sqlite_session.query(DaySummary).count() == 0


def test_run_index_job_marks_duration_mismatch_as_warning(
    sqlite_session,
    monkeypatch,
    tmp_path,
):
    file_name = "00_20260317000000_20260317001000.mp4"
    file_path = tmp_path / file_name
    file_path.write_bytes(b"x")

    monkeypatch.setattr(
        "app.tasks.index_videos.scan_video_files",
        lambda _: [
            type(
                "ScannedVideoFile",
                (),
                {
                    "path": file_path,
                    "name": file_name,
                    "file_size": 1,
                    "file_mtime": 1711209600,
                },
            )()
        ],
    )
    monkeypatch.setattr(
        "app.tasks.index_videos.probe_media",
        lambda _: ProbeResult(duration_sec=620.0, start_time_sec=0.0),
    )

    job = run_index_job(sqlite_session, root=tmp_path)

    stored_file = sqlite_session.query(VideoFile).one()
    assert stored_file.status == "warning"
    assert "duration_mismatch" in json.loads(stored_file.issue_flags)

    stored_segment = sqlite_session.query(TimelineSegment).one()
    assert stored_segment.status == "warning"

    summary = sqlite_session.get(DaySummary, "2026-03-17")
    assert summary is not None
    assert summary.has_warning is True

    assert job.warning_count == 1
    assert job.success_count == 0
    assert job.failed_count == 0


def test_run_index_job_target_day_includes_new_file_that_actual_range_crosses_next_day(
    sqlite_session,
    monkeypatch,
    tmp_path,
):
    file_name = "00_20260317235500_20260317235900.mp4"
    file_path = tmp_path / file_name
    file_path.write_bytes(b"x")

    monkeypatch.setattr(
        "app.tasks.index_videos.scan_video_files",
        lambda _: [
            type(
                "ScannedVideoFile",
                (),
                {
                    "path": file_path,
                    "name": file_name,
                    "file_size": 1,
                    "file_mtime": 1711238100,
                },
            )()
        ],
    )
    monkeypatch.setattr(
        "app.tasks.index_videos.probe_media",
        lambda _: ProbeResult(duration_sec=600.0, start_time_sec=0.0),
    )

    job = run_index_job(sqlite_session, root=tmp_path, target_day="2026-03-18")

    assert job.scanned_count == 1
    assert job.warning_count == 1
    assert job.failed_count == 0

    stored_file = sqlite_session.query(VideoFile).one()
    assert stored_file.actual_start_at == "2026-03-17T23:55:00+08:00"
    assert stored_file.actual_end_at == "2026-03-18T00:05:00+08:00"

    next_day_segments = (
        sqlite_session.query(TimelineSegment)
        .filter(TimelineSegment.day == "2026-03-18")
        .all()
    )
    assert len(next_day_segments) == 1
    assert next_day_segments[0].segment_start_at == "2026-03-18T00:00:00+08:00"
    assert next_day_segments[0].segment_end_at == "2026-03-18T00:05:00+08:00"

    summary = sqlite_session.get(DaySummary, "2026-03-18")
    assert summary is not None
    assert summary.total_segment_count == 1
    assert summary.total_recorded_sec == 300.0
    assert summary.has_warning is True
