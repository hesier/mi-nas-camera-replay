from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.db import Base
from app.core.db import SessionLocal
from app.models import IndexJob, VideoFile
from app.services.file_scanner import scan_video_files, should_reprobe
from app.services.filename_parser import parse_camera_filename
from app.services.media_probe import probe_media
from app.tasks.rebuild_day import (
    collect_impacted_days,
    rebuild_day_timeline,
    rebuild_impacted_days,
)


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat()


def _serialize_issue_flags(issue_flags: list[str]) -> str:
    return json.dumps(issue_flags)


def _build_video_file_payload(incoming_file, now_iso: str) -> dict[str, object]:
    parsed = parse_camera_filename(incoming_file.name)
    probe = probe_media(str(incoming_file.path))
    actual_start_at = parsed.name_start_at
    actual_end_at = actual_start_at + timedelta(seconds=probe.duration_sec)
    return {
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
        "status": "ready",
        "issue_flags": _serialize_issue_flags([]),
        "updated_at": now_iso,
    }


def _upsert_video_file(
    session: Session,
    incoming_file,
    now_iso: str,
) -> tuple[VideoFile, set[str], bool]:
    existing = (
        session.query(VideoFile)
        .filter(VideoFile.file_path == str(incoming_file.path))
        .one_or_none()
    )
    if existing is not None and not should_reprobe(existing, incoming_file):
        return existing, set(), False

    previous_days = set(collect_impacted_days(existing)) if existing is not None else set()
    payload = _build_video_file_payload(incoming_file, now_iso)

    if existing is None:
        file_record = VideoFile(created_at=now_iso, **payload)
        session.add(file_record)
        session.flush()
    else:
        for key, value in payload.items():
            setattr(existing, key, value)
        file_record = existing
        session.flush()

    return file_record, previous_days, True


def run_index_job(
    session: Session,
    root: str | Path | None = None,
    target_day: str | None = None,
) -> IndexJob:
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

    scanned_files = scan_video_files(root or get_settings().video_root)
    if target_day is not None:
        filtered_files = []
        for incoming_file in scanned_files:
            try:
                parsed = parse_camera_filename(incoming_file.name)
            except ValueError:
                continue
            day_span = {
                parsed.name_start_at.date().isoformat(),
                parsed.name_end_at.date().isoformat(),
            }
            if target_day in day_span:
                filtered_files.append(incoming_file)
        scanned_files = filtered_files

    scanned_count = 0
    success_count = 0
    warning_count = 0
    failed_count = 0

    for incoming_file in scanned_files:
        scanned_count += 1
        try:
            file_record, previous_days, changed = _upsert_video_file(
                session=session,
                incoming_file=incoming_file,
                now_iso=_now_iso(),
            )
        except ValueError:
            failed_count += 1
            session.rollback()
            continue

        if changed:
            current_days = set(collect_impacted_days(file_record))
            for day in sorted(previous_days - current_days):
                rebuild_day_timeline(session, day)
            rebuild_impacted_days(session, file_record)
            session.commit()

        if file_record.status == "warning":
            warning_count += 1
        else:
            success_count += 1

    job.scanned_count = scanned_count
    job.success_count = success_count
    job.warning_count = warning_count
    job.failed_count = failed_count
    job.finished_at = _now_iso()
    job.status = "success" if failed_count == 0 else "warning"
    session.add(job)
    session.commit()
    session.refresh(job)
    return job


def main() -> int:
    parser = argparse.ArgumentParser(description="索引视频文件")
    parser.add_argument("--day", dest="target_day", default=None)
    args = parser.parse_args()

    session = SessionLocal()
    try:
        job = run_index_job(
            session=session,
            root=get_settings().video_root,
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
