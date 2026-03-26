from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.core.config import CameraRoot
from app.models import DaySummary, IndexJob, TimelineSegment, VideoFile
from app.services.media_probe import ProbeResult
from app.tasks.rebuild_day import rebuild_day_timeline
from app.tasks.index_videos import enqueue_index_job, run_index_job


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
    assert stored_file.camera_no == 1
    assert stored_file.actual_end_at == "2026-03-17T00:10:00+08:00"

    stored_segments = sqlite_session.query(TimelineSegment).all()
    assert len(stored_segments) == 1
    assert stored_segments[0].day == "2026-03-17"
    assert stored_segments[0].playback_url == f"/api/videos/{stored_file.id}/stream"

    summary = (
        sqlite_session.query(DaySummary)
        .filter(DaySummary.camera_no == 1, DaySummary.day == "2026-03-17")
        .one_or_none()
    )
    assert summary is not None
    assert summary.total_segment_count == 1
    assert summary.total_recorded_sec == 600.0
    assert summary.total_gap_sec == 0.0
    assert summary.has_warning is False


def test_run_index_job_persists_camera_no_and_isolates_day_summary_by_camera(
    sqlite_session,
    monkeypatch,
    tmp_path,
):
    cam1_root = tmp_path / "cam1"
    cam2_root = tmp_path / "cam2"
    cam1_root.mkdir()
    cam2_root.mkdir()

    file_name_1 = "00_20260317000000_20260317001000.mp4"
    file_path_1 = cam1_root / file_name_1
    file_path_1.write_bytes(b"x")

    file_name_2 = "00_20260317000000_20260317002000.mp4"
    file_path_2 = cam2_root / file_name_2
    file_path_2.write_bytes(b"y")

    def fake_scan(root: str):
        if str(root) == str(cam1_root):
            return [
                type(
                    "ScannedVideoFile",
                    (),
                    {
                        "path": file_path_1,
                        "name": file_name_1,
                        "file_size": 1,
                        "file_mtime": 1711209600,
                    },
                )()
            ]
        if str(root) == str(cam2_root):
            return [
                type(
                    "ScannedVideoFile",
                    (),
                    {
                        "path": file_path_2,
                        "name": file_name_2,
                        "file_size": 1,
                        "file_mtime": 1711209600,
                    },
                )()
            ]
        raise AssertionError(f"未知 root: {root}")

    monkeypatch.setattr("app.tasks.index_videos.scan_video_files", fake_scan)
    monkeypatch.setattr(
        "app.tasks.index_videos.probe_media",
        lambda _: ProbeResult(duration_sec=600.0, start_time_sec=0.0),
    )

    job = run_index_job(
        sqlite_session,
        camera_roots=[
            CameraRoot(camera_no=1, video_root=str(cam1_root)),
            CameraRoot(camera_no=2, video_root=str(cam2_root)),
        ],
    )

    assert job.scanned_count == 2
    assert sqlite_session.query(VideoFile).count() == 2

    files = {f.camera_no: f for f in sqlite_session.query(VideoFile).all()}
    assert files[1].file_path == str(file_path_1)
    assert files[2].file_path == str(file_path_2)

    # 同一天不同通道应各自生成 day_summary，且不会混写到同一条
    summaries = (
        sqlite_session.query(DaySummary)
        .filter(DaySummary.day == "2026-03-17")
        .order_by(DaySummary.camera_no.asc())
        .all()
    )
    assert [(s.camera_no, s.total_segment_count) for s in summaries] == [(1, 1), (2, 1)]

    segments = (
        sqlite_session.query(TimelineSegment)
        .filter(TimelineSegment.day == "2026-03-17")
        .order_by(TimelineSegment.camera_no.asc())
        .all()
    )
    assert len(segments) == 2
    assert segments[0].camera_no == 1
    assert segments[1].camera_no == 2


def test_rebuild_day_timeline_only_affects_target_camera(sqlite_session):
    day = "2026-03-17"
    sqlite_session.add(
        TimelineSegment(
            file_id=1,
            camera_no=1,
            day=day,
            segment_start_at="2026-03-17T00:01:00+08:00",
            segment_end_at="2026-03-17T00:02:00+08:00",
            duration_sec=60.0,
            playback_url="/stale/url/1",
            file_offset_sec=0.0,
            prev_gap_sec=None,
            next_gap_sec=None,
            status="warning",
        )
    )
    sqlite_session.add(
        TimelineSegment(
            file_id=2,
            camera_no=2,
            day=day,
            segment_start_at="2026-03-17T00:03:00+08:00",
            segment_end_at="2026-03-17T00:04:00+08:00",
            duration_sec=60.0,
            playback_url="/stale/url/2",
            file_offset_sec=0.0,
            prev_gap_sec=None,
            next_gap_sec=None,
            status="warning",
        )
    )
    sqlite_session.add(
        DaySummary(
            camera_no=1,
            day=day,
            first_segment_at="2026-03-17T00:01:00+08:00",
            last_segment_at="2026-03-17T00:02:00+08:00",
            total_segment_count=1,
            total_recorded_sec=60.0,
            total_gap_sec=0.0,
            has_warning=True,
            updated_at="2026-03-24T00:00:00+08:00",
        )
    )
    sqlite_session.add(
        DaySummary(
            camera_no=2,
            day=day,
            first_segment_at="2026-03-17T00:03:00+08:00",
            last_segment_at="2026-03-17T00:04:00+08:00",
            total_segment_count=1,
            total_recorded_sec=60.0,
            total_gap_sec=0.0,
            has_warning=True,
            updated_at="2026-03-24T00:00:00+08:00",
        )
    )
    sqlite_session.commit()

    rebuild_day_timeline(sqlite_session, 1, day)
    sqlite_session.commit()

    # camera=1 的 segment / summary 应被清理（无 source_files），camera=2 保持不变
    assert (
        sqlite_session.query(TimelineSegment)
        .filter(TimelineSegment.camera_no == 1, TimelineSegment.day == day)
        .count()
        == 0
    )
    assert (
        sqlite_session.query(DaySummary)
        .filter(DaySummary.camera_no == 1, DaySummary.day == day)
        .one_or_none()
        is None
    )
    assert (
        sqlite_session.query(TimelineSegment)
        .filter(TimelineSegment.camera_no == 2, TimelineSegment.day == day)
        .count()
        == 1
    )
    assert (
        sqlite_session.query(DaySummary)
        .filter(DaySummary.camera_no == 2, DaySummary.day == day)
        .one_or_none()
        is not None
    )


def test_run_index_job_updates_camera_no_even_when_file_unchanged_and_cleans_old_camera_data(
    sqlite_session,
    monkeypatch,
    tmp_path,
):
    cam2_root = tmp_path / "cam2"
    cam2_root.mkdir()

    file_name = "00_20260317000000_20260317001000.mp4"
    file_path = cam2_root / file_name
    file_path.write_bytes(b"x")

    # 旧库里同一路径文件被错误地归到 camera=1，且已有 timeline/day_summary
    sqlite_session.add(
        VideoFile(
            camera_no=1,
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
            camera_no=1,
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
            camera_no=1,
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
        lambda root: [
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
        lambda _: (_ for _ in ()).throw(AssertionError("未变化文件仅迁移通道时不应重新探测")),
    )

    job = run_index_job(
        sqlite_session,
        camera_roots=[CameraRoot(camera_no=2, video_root=str(cam2_root))],
    )

    assert job.scanned_count == 1
    assert sqlite_session.query(VideoFile).one().camera_no == 2

    # 旧通道脏数据必须被清理
    assert (
        sqlite_session.query(TimelineSegment)
        .filter(TimelineSegment.camera_no == 1, TimelineSegment.day == "2026-03-17")
        .count()
        == 0
    )
    assert (
        sqlite_session.query(DaySummary)
        .filter(DaySummary.camera_no == 1, DaySummary.day == "2026-03-17")
        .one_or_none()
        is None
    )

    # 新通道应生成对应 timeline/day_summary
    assert (
        sqlite_session.query(TimelineSegment)
        .filter(TimelineSegment.camera_no == 2, TimelineSegment.day == "2026-03-17")
        .count()
        == 1
    )
    assert (
        sqlite_session.query(DaySummary)
        .filter(DaySummary.camera_no == 2, DaySummary.day == "2026-03-17")
        .one_or_none()
        is not None
    )


def test_run_index_job_invalid_file_migration_cleans_old_camera_data(
    sqlite_session,
    monkeypatch,
    tmp_path,
):
    cam2_root = tmp_path / "cam2"
    cam2_root.mkdir()

    file_name = "bad.mp4"
    file_path = cam2_root / file_name
    file_path.write_bytes(b"x")

    # 旧库里同一路径文件被错误归到 camera=1，且曾参与过 timeline/day_summary
    sqlite_session.add(
        VideoFile(
            camera_no=1,
            file_path=str(file_path),
            file_name="00_20260317000000_20260317001000.mp4",
            file_size=2,  # 强制 should_reprobe=True 触发无效文件分支
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
            camera_no=1,
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
            camera_no=1,
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
        lambda root: [
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
        lambda _: (_ for _ in ()).throw(AssertionError("无效文件分支不应探测媒体")),
    )

    job = run_index_job(
        sqlite_session,
        camera_roots=[CameraRoot(camera_no=2, video_root=str(cam2_root))],
    )

    assert job.failed_count == 1
    assert sqlite_session.query(VideoFile).one().camera_no == 2

    # 旧通道脏数据必须被清理
    assert (
        sqlite_session.query(TimelineSegment)
        .filter(TimelineSegment.camera_no == 1, TimelineSegment.day == "2026-03-17")
        .count()
        == 0
    )
    assert (
        sqlite_session.query(DaySummary)
        .filter(DaySummary.camera_no == 1, DaySummary.day == "2026-03-17")
        .one_or_none()
        is None
    )


def test_enqueue_index_job_creates_running_job_and_schedules_background_work(
    sqlite_session,
    monkeypatch,
):
    scheduled = {}

    def fake_start_background_thread(target, *args):
        scheduled["target"] = target
        scheduled["args"] = args
        return None

    session_factory = lambda: sqlite_session

    monkeypatch.setattr(
        "app.tasks.index_videos._start_background_thread",
        fake_start_background_thread,
    )
    monkeypatch.setattr(
        "app.tasks.index_videos._run_index_job_with_existing_job",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("enqueue 不应同步执行完整索引任务")
        ),
    )

    job = enqueue_index_job(
        target_day="2026-03-18",
        session_factory=session_factory,
    )

    stored_job = sqlite_session.get(IndexJob, job.id)
    assert stored_job is not None
    assert stored_job.status == "running"
    assert stored_job.job_day == "2026-03-18"
    assert stored_job.finished_at is None
    assert scheduled["target"].__name__ == "_run_index_job_in_background"
    assert scheduled["args"][0] == job.id
    assert scheduled["args"][3] == "2026-03-18"


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
            camera_no=1,
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

    assert (
        sqlite_session.query(DaySummary)
        .filter(DaySummary.camera_no == 1, DaySummary.day == "2026-03-17")
        .count()
        == 1
    )
    summary = (
        sqlite_session.query(DaySummary)
        .filter(DaySummary.camera_no == 1, DaySummary.day == "2026-03-17")
        .one_or_none()
    )
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

    summary = (
        sqlite_session.query(DaySummary)
        .filter(DaySummary.camera_no == 1, DaySummary.day == "2026-03-17")
        .one_or_none()
    )
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

    summary = (
        sqlite_session.query(DaySummary)
        .filter(DaySummary.camera_no == 1, DaySummary.day == "2026-03-18")
        .one_or_none()
    )
    assert summary is not None
    assert summary.total_segment_count == 1
    assert summary.total_recorded_sec == 300.0
    assert summary.has_warning is True


def test_run_index_job_target_day_includes_changed_existing_file_that_new_range_crosses_next_day(
    sqlite_session,
    monkeypatch,
    tmp_path,
):
    file_name = "00_20260317235500_20260317235900.mp4"
    file_path = tmp_path / file_name
    file_path.write_bytes(b"xx")

    sqlite_session.add(
        VideoFile(
            file_path=str(file_path),
            file_name=file_name,
            file_size=1,
            file_mtime=1711238000,
            name_start_at="2026-03-17T23:55:00+08:00",
            name_end_at="2026-03-17T23:59:00+08:00",
            probe_duration_sec=240.0,
            probe_video_codec=None,
            probe_audio_codec=None,
            probe_width=None,
            probe_height=None,
            probe_start_time_sec=0.0,
            actual_start_at="2026-03-17T23:55:00+08:00",
            actual_end_at="2026-03-17T23:59:00+08:00",
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
                    "file_size": 2,
                    "file_mtime": 1711238100,
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

    job = run_index_job(sqlite_session, root=tmp_path, target_day="2026-03-18")

    assert probe_called is True
    assert job.scanned_count == 1
    assert job.failed_count == 0

    stored_file = sqlite_session.query(VideoFile).one()
    assert stored_file.file_size == 2
    assert stored_file.file_mtime == 1711238100
    assert stored_file.actual_end_at == "2026-03-18T00:05:00+08:00"

    next_day_segments = (
        sqlite_session.query(TimelineSegment)
        .filter(TimelineSegment.day == "2026-03-18")
        .all()
    )
    assert len(next_day_segments) == 1
    assert next_day_segments[0].segment_start_at == "2026-03-18T00:00:00+08:00"
    assert next_day_segments[0].segment_end_at == "2026-03-18T00:05:00+08:00"

    summary = (
        sqlite_session.query(DaySummary)
        .filter(DaySummary.camera_no == 1, DaySummary.day == "2026-03-18")
        .one_or_none()
    )
    assert summary is not None
    assert summary.total_segment_count == 1
    assert summary.total_recorded_sec == 300.0


def test_run_index_job_marks_job_failed_when_unexpected_error_occurs(
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
    monkeypatch.setattr(
        "app.tasks.index_videos.rebuild_impacted_days",
        lambda *_: (_ for _ in ()).throw(RuntimeError("boom")),
    )

    with pytest.raises(RuntimeError, match="boom"):
        run_index_job(sqlite_session, root=tmp_path)

    stored_job = sqlite_session.query(IndexJob).one()
    assert stored_job.status == "failed"
    assert stored_job.finished_at is not None


def test_run_index_job_does_not_count_unchanged_invalid_file_as_success(
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
            probe_duration_sec=None,
            probe_video_codec=None,
            probe_audio_codec=None,
            probe_width=None,
            probe_height=None,
            probe_start_time_sec=None,
            actual_start_at=None,
            actual_end_at=None,
            time_source="filename",
            status="invalid",
            issue_flags='["invalid_media"]',
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

    job = run_index_job(sqlite_session, root=tmp_path)

    assert job.scanned_count == 1
    assert job.success_count == 0
    assert job.failed_count == 1
    assert job.status == "warning"


def test_run_index_job_target_day_skips_obviously_old_new_file_candidates(
    sqlite_session,
    monkeypatch,
    tmp_path,
):
    file_name = "00_20260316235500_20260316235900.mp4"
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
                    "file_mtime": 1711151700,
                },
            )()
        ],
    )
    monkeypatch.setattr(
        "app.tasks.index_videos.probe_media",
        lambda _: (_ for _ in ()).throw(AssertionError("明显过旧文件不应进入探测")),
    )

    job = run_index_job(sqlite_session, root=tmp_path, target_day="2026-03-18")

    assert job.scanned_count == 0
    assert sqlite_session.query(VideoFile).count() == 0
