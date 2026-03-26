from __future__ import annotations

import argparse
import json
import logging
from collections.abc import Callable
from datetime import date, datetime, timedelta
from pathlib import Path
from threading import Thread

from sqlalchemy.orm import Session

from app.core.config import CameraRoot, get_settings
from app.core.db import Base, assert_sqlite_schema_compatible
from app.core.db import SessionLocal
from app.models import IndexJob, VideoFile
from app.services.file_scanner import scan_video_files, should_reprobe
from app.services.filename_parser import ParsedFilename, parse_camera_filename
from app.services.media_probe import probe_media
from app.services.timeline_builder import DURATION_MISMATCH_SEC
from app.tasks.rebuild_day import (
    collect_impacted_days,
    rebuild_day_timeline,
    rebuild_impacted_days,
)

logger = logging.getLogger(__name__)


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat()


def _serialize_issue_flags(issue_flags: list[str]) -> str:
    return json.dumps(issue_flags)


def _build_video_file_status(
    parsed: ParsedFilename,
    probe_duration_sec: float,
) -> tuple[str, list[str]]:
    expected_duration_sec = (
        parsed.name_end_at - parsed.name_start_at
    ).total_seconds()
    issue_flags: list[str] = []
    if abs(expected_duration_sec - probe_duration_sec) > DURATION_MISMATCH_SEC:
        issue_flags.append("duration_mismatch")
    status = "warning" if issue_flags else "ready"
    return status, issue_flags


def _parse_filename_or_none(file_name: str) -> ParsedFilename | None:
    try:
        return parse_camera_filename(file_name)
    except ValueError:
        return None


def _parse_day(value: str) -> date:
    return date.fromisoformat(value)


def _is_target_day_candidate_from_filename(
    parsed: ParsedFilename,
    target_day: str,
) -> bool:
    candidate_day = _parse_day(target_day)
    latest_possible_day = parsed.name_end_at.date() + timedelta(days=1)
    return parsed.name_start_at.date() <= candidate_day <= latest_possible_day


def _should_scan_for_target_day(
    session: Session,
    incoming_file,
    target_day: str,
) -> bool:
    existing = (
        session.query(VideoFile)
        .filter(VideoFile.file_path == str(incoming_file.path))
        .one_or_none()
    )
    if existing is not None and not should_reprobe(existing, incoming_file):
        return target_day in collect_impacted_days(existing)

    parsed = _parse_filename_or_none(incoming_file.name)
    if parsed is None:
        return False
    return _is_target_day_candidate_from_filename(parsed, target_day)


def _build_video_file_payload(
    incoming_file,
    now_iso: str,
    parsed: ParsedFilename,
    *,
    camera_no: int,
) -> dict[str, object]:
    probe = probe_media(str(incoming_file.path))
    actual_start_at = parsed.name_start_at
    actual_end_at = actual_start_at + timedelta(seconds=probe.duration_sec)
    status, issue_flags = _build_video_file_status(parsed, probe.duration_sec)
    return {
        "camera_no": camera_no,
        "file_path": str(incoming_file.path),
        "file_name": incoming_file.name,
        "file_size": incoming_file.file_size,
        "file_mtime": incoming_file.file_mtime,
        "name_start_at": parsed.name_start_at.isoformat(),
        "name_end_at": parsed.name_end_at.isoformat(),
        "probe_duration_sec": probe.duration_sec,
        "probe_video_codec": None,
        "probe_audio_codec": None,
        "probe_width": None,
        "probe_height": None,
        "probe_start_time_sec": probe.start_time_sec,
        "actual_start_at": actual_start_at.isoformat(),
        "actual_end_at": actual_end_at.isoformat(),
        "time_source": "filename",
        "status": status,
        "issue_flags": _serialize_issue_flags(issue_flags),
        "updated_at": now_iso,
    }


def _upsert_video_file(
    session: Session,
    incoming_file,
    now_iso: str,
    *,
    camera_no: int,
) -> tuple[VideoFile, set[str], bool, int | None]:
    existing = (
        session.query(VideoFile)
        .filter(VideoFile.file_path == str(incoming_file.path))
        .one_or_none()
    )
    if existing is not None and not should_reprobe(existing, incoming_file):
        previous_camera_no = int(existing.camera_no)
        if previous_camera_no == camera_no:
            return existing, set(), False, previous_camera_no

        # 文件内容未变化，但来源通道变更：需要迁移 camera_no，并触发旧通道清理
        previous_days = set(collect_impacted_days(existing))
        existing.camera_no = camera_no
        existing.updated_at = now_iso
        session.flush()
        return existing, previous_days, True, previous_camera_no

    previous_days = set(collect_impacted_days(existing)) if existing is not None else set()
    previous_camera_no = int(existing.camera_no) if existing is not None else None
    parsed = parse_camera_filename(incoming_file.name)
    payload = _build_video_file_payload(
        incoming_file,
        now_iso,
        parsed,
        camera_no=camera_no,
    )

    if existing is None:
        file_record = VideoFile(created_at=now_iso, **payload)
        session.add(file_record)
        session.flush()
    else:
        for key, value in payload.items():
            setattr(existing, key, value)
        file_record = existing
        session.flush()

    return file_record, previous_days, True, previous_camera_no


def _upsert_invalid_video_file(
    session: Session,
    incoming_file,
    now_iso: str,
    *,
    camera_no: int,
    issue_flag: str = "invalid_media",
) -> tuple[VideoFile, set[str], int | None]:
    existing = (
        session.query(VideoFile)
        .filter(VideoFile.file_path == str(incoming_file.path))
        .one_or_none()
    )
    previous_days = set(collect_impacted_days(existing)) if existing is not None else set()
    previous_camera_no = int(existing.camera_no) if existing is not None else None
    parsed = _parse_filename_or_none(incoming_file.name)

    payload = {
        "camera_no": camera_no,
        "file_path": str(incoming_file.path),
        "file_name": incoming_file.name,
        "file_size": incoming_file.file_size,
        "file_mtime": incoming_file.file_mtime,
        "name_start_at": parsed.name_start_at.isoformat() if parsed is not None else None,
        "name_end_at": parsed.name_end_at.isoformat() if parsed is not None else None,
        "probe_duration_sec": None,
        "probe_video_codec": None,
        "probe_audio_codec": None,
        "probe_width": None,
        "probe_height": None,
        "probe_start_time_sec": None,
        "actual_start_at": None,
        "actual_end_at": None,
        "time_source": "filename" if parsed is not None else "unknown",
        "status": "invalid",
        "issue_flags": _serialize_issue_flags([issue_flag]),
        "updated_at": now_iso,
    }

    if existing is None:
        file_record = VideoFile(created_at=now_iso, **payload)
        session.add(file_record)
    else:
        for key, value in payload.items():
            setattr(existing, key, value)
        file_record = existing

    session.flush()
    return file_record, previous_days, previous_camera_no


def _normalize_camera_roots(
    *,
    camera_roots: list[CameraRoot] | None,
    root: str | Path | None,
) -> list[CameraRoot]:
    if camera_roots is not None and root is not None:
        raise ValueError("camera_roots 与 root 不允许同时传入")

    if camera_roots is not None:
        return camera_roots

    # 兼容旧入口：仅传 root 时默认 camera_no=1
    if root is not None:
        return [CameraRoot(camera_no=1, video_root=str(root))]

    # 兼容旧 API 语义：无参调用默认仍只扫单通道（VIDEO_ROOT / VIDEO_ROOT_1）
    return [CameraRoot(camera_no=1, video_root=str(get_settings().video_root))]


def _update_job_counters(
    file_record: VideoFile,
    *,
    success_count: int,
    warning_count: int,
    failed_count: int,
) -> tuple[int, int, int]:
    if file_record.status == "warning":
        return success_count, warning_count + 1, failed_count
    if file_record.status == "invalid":
        return success_count, warning_count, failed_count + 1
    return success_count + 1, warning_count, failed_count


def _finalize_job(
    session: Session,
    job_id: int,
    *,
    scanned_count: int,
    success_count: int,
    warning_count: int,
    failed_count: int,
    status: str,
) -> IndexJob:
    job = session.get(IndexJob, job_id)
    if job is None:
        raise ValueError("index job missing")
    job.scanned_count = scanned_count
    job.success_count = success_count
    job.warning_count = warning_count
    job.failed_count = failed_count
    job.finished_at = _now_iso()
    job.status = status
    session.add(job)
    session.commit()
    session.refresh(job)
    return job


def create_index_job(
    session: Session,
    *,
    target_day: str | None,
) -> IndexJob:
    assert_sqlite_schema_compatible(session.get_bind())
    Base.metadata.create_all(bind=session.get_bind())
    job = IndexJob(
        job_day=target_day or "all",
        status="running",
        started_at=_now_iso(),
        scanned_count=0,
        success_count=0,
        warning_count=0,
        failed_count=0,
    )
    session.add(job)
    session.commit()
    session.refresh(job)
    return job


def _run_index_job_with_existing_job(
    session: Session,
    job_id: int,
    *,
    camera_roots: list[CameraRoot] | None = None,
    root: str | Path | None = None,
    target_day: str | None = None,
) -> IndexJob:
    Base.metadata.create_all(bind=session.get_bind())

    scanned_count = 0
    success_count = 0
    warning_count = 0
    failed_count = 0

    try:
        effective_camera_roots = _normalize_camera_roots(
            camera_roots=camera_roots,
            root=root,
        )

        for camera_root in effective_camera_roots:
            scanned_files = scan_video_files(camera_root.video_root)
            if target_day is not None:
                scanned_files = [
                    incoming_file
                    for incoming_file in scanned_files
                    if _should_scan_for_target_day(session, incoming_file, target_day)
                ]

            for incoming_file in scanned_files:
                scanned_count += 1
                try:
                    file_record, previous_days, changed, previous_camera_no = _upsert_video_file(
                        session=session,
                        incoming_file=incoming_file,
                        now_iso=_now_iso(),
                        camera_no=camera_root.camera_no,
                    )
                except ValueError:
                    invalid_record, previous_days, previous_camera_no = _upsert_invalid_video_file(
                        session=session,
                        incoming_file=incoming_file,
                        now_iso=_now_iso(),
                        camera_no=camera_root.camera_no,
                    )
                    for day in sorted(previous_days):
                        # 文件可能从旧通道迁移到新通道，需要先清理旧通道
                        if (
                            previous_camera_no is not None
                            and previous_camera_no != int(invalid_record.camera_no)
                        ):
                            rebuild_day_timeline(session, previous_camera_no, day)
                        rebuild_day_timeline(session, int(invalid_record.camera_no), day)
                    session.commit()
                    failed_count += 1
                    continue

                if changed:
                    current_days = set(collect_impacted_days(file_record))
                    current_camera_no = int(file_record.camera_no)

                    # 文件归属通道发生变化时，旧通道必须重建/清理受影响日期
                    if (
                        previous_camera_no is not None
                        and previous_camera_no != current_camera_no
                    ):
                        for day in sorted(previous_days):
                            rebuild_day_timeline(session, previous_camera_no, day)

                    # 文件日期范围发生变化时，需要清理当前通道中已不再受影响的日期
                    if previous_camera_no == current_camera_no:
                        for day in sorted(previous_days - current_days):
                            rebuild_day_timeline(session, current_camera_no, day)
                    rebuild_impacted_days(session, file_record)
                    session.commit()

                success_count, warning_count, failed_count = _update_job_counters(
                    file_record,
                    success_count=success_count,
                    warning_count=warning_count,
                    failed_count=failed_count,
                )

        if target_day is not None:
            # target_day 模式需要确保指定日期的 timeline 被重建（即使文件未变化）。
            for camera_root in effective_camera_roots:
                rebuild_day_timeline(session, camera_root.camera_no, target_day)
            session.commit()
    except Exception:
        session.rollback()
        _finalize_job(
            session,
            job_id,
            scanned_count=scanned_count,
            success_count=success_count,
            warning_count=warning_count,
            failed_count=failed_count,
            status="failed",
        )
        raise

    return _finalize_job(
        session,
        job_id,
        scanned_count=scanned_count,
        success_count=success_count,
        warning_count=warning_count,
        failed_count=failed_count,
        status="success" if failed_count == 0 else "warning",
    )


def run_index_job(
    session: Session,
    *,
    camera_roots: list[CameraRoot] | None = None,
    root: str | Path | None = None,
    target_day: str | None = None,
) -> IndexJob:
    job = create_index_job(session, target_day=target_day)
    return _run_index_job_with_existing_job(
        session,
        job.id,
        camera_roots=camera_roots,
        root=root,
        target_day=target_day,
    )


def _start_background_thread(
    target,
    *args,
) -> Thread:
    thread = Thread(target=target, args=args, daemon=True)
    thread.start()
    return thread


def _run_index_job_in_background(
    job_id: int,
    camera_roots: list[CameraRoot] | None,
    root: str | Path | None,
    target_day: str | None,
    session_factory: Callable[[], Session],
) -> None:
    session = session_factory()
    try:
        _run_index_job_with_existing_job(
            session,
            job_id,
            camera_roots=camera_roots,
            root=root,
            target_day=target_day,
        )
    except Exception:
        logger.exception("后台索引任务执行失败", extra={"job_id": job_id})
    finally:
        session.close()


def start_background_index_job(
    job_id: int,
    *,
    camera_roots: list[CameraRoot] | None = None,
    root: str | Path | None = None,
    target_day: str | None = None,
    session_factory: Callable[[], Session] = SessionLocal,
) -> Thread:
    return _start_background_thread(
        _run_index_job_in_background,
        job_id,
        camera_roots,
        root,
        target_day,
        session_factory,
    )


def enqueue_index_job(
    *,
    camera_roots: list[CameraRoot] | None = None,
    root: str | Path | None = None,
    target_day: str | None = None,
    session_factory: Callable[[], Session] = SessionLocal,
) -> IndexJob:
    session = session_factory()
    try:
        job = create_index_job(session, target_day=target_day)
    finally:
        session.close()

    start_background_index_job(
        job.id,
        camera_roots=camera_roots,
        root=root,
        target_day=target_day,
        session_factory=session_factory,
    )
    return job


def main() -> int:
    parser = argparse.ArgumentParser(description="索引视频文件")
    parser.add_argument("--day", dest="target_day", default=None)
    args = parser.parse_args()

    session = SessionLocal()
    try:
        job = run_index_job(
            session=session,
            camera_roots=get_settings().camera_roots,
            target_day=args.target_day,
        )
    finally:
        session.close()

    print(
        f"scanned={job.scanned_count} success={job.success_count} "
        f"warning={job.warning_count} failed={job.failed_count}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
