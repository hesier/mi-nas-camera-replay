from __future__ import annotations

from datetime import datetime, time, timedelta

from sqlalchemy.orm import Session

from app.models import DaySummary, TimelineSegment, VideoFile
from app.services.timeline_builder import (
    DaySummarySnapshot,
    TimelineSourceFile,
    build_timelines_by_day,
)


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat()


def _parse_iso_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value)


def collect_impacted_days(file_record: VideoFile) -> list[str]:
    start_at = _parse_iso_datetime(file_record.actual_start_at) or _parse_iso_datetime(
        file_record.name_start_at
    )
    end_at = _parse_iso_datetime(file_record.actual_end_at) or _parse_iso_datetime(
        file_record.name_end_at
    )
    if start_at is None or end_at is None:
        return []

    effective_end_at = end_at
    if end_at > start_at and end_at.timetz().replace(tzinfo=None) == time.min:
        effective_end_at = end_at - timedelta(microseconds=1)

    day_cursor = start_at.date()
    end_day = effective_end_at.date()
    impacted_days: list[str] = []
    while day_cursor <= end_day:
        impacted_days.append(day_cursor.isoformat())
        day_cursor += timedelta(days=1)
    return impacted_days


def _build_timeline_source(record: VideoFile) -> TimelineSourceFile | None:
    if (
        record.id is None
        or record.name_start_at is None
        or record.name_end_at is None
        or record.probe_duration_sec is None
    ):
        return None
    return TimelineSourceFile(
        file_id=record.id,
        file_name=record.file_name,
        playback_url=f"/api/videos/{record.id}/stream",
        name_start_at=datetime.fromisoformat(record.name_start_at),
        name_end_at=datetime.fromisoformat(record.name_end_at),
        probe_duration_sec=float(record.probe_duration_sec),
    )


def _load_day_source_files(session: Session, day: str) -> list[TimelineSourceFile]:
    source_files: list[TimelineSourceFile] = []
    records = (
        session.query(VideoFile)
        .filter(VideoFile.status.in_(("ready", "warning")))
        .order_by(VideoFile.id.asc())
        .all()
    )
    for record in records:
        if day not in collect_impacted_days(record):
            continue
        source = _build_timeline_source(record)
        if source is not None:
            source_files.append(source)
    return source_files


def upsert_day_summary(session: Session, day: str, summary: DaySummarySnapshot) -> DaySummary:
    current = session.get(DaySummary, day)
    payload = {
        "first_segment_at": (
            summary.first_segment_at.isoformat()
            if summary.first_segment_at is not None
            else None
        ),
        "last_segment_at": (
            summary.last_segment_at.isoformat()
            if summary.last_segment_at is not None
            else None
        ),
        "total_segment_count": summary.total_segment_count,
        "total_recorded_sec": summary.total_recorded_sec,
        "total_gap_sec": summary.total_gap_sec,
        "has_warning": summary.has_warning,
        "updated_at": _now_iso(),
    }
    if current is None:
        current = DaySummary(day=day, **payload)
        session.add(current)
    else:
        for key, value in payload.items():
            setattr(current, key, value)
    return current


def rebuild_day_timeline(session: Session, day: str):
    session.query(TimelineSegment).filter(TimelineSegment.day == day).delete()

    source_files = _load_day_source_files(session, day)
    if not source_files:
        summary = session.get(DaySummary, day)
        if summary is not None:
            session.delete(summary)
        session.flush()
        return None

    build_result = build_timelines_by_day(source_files).get(day)
    if build_result is None:
        session.flush()
        return None

    for segment in build_result.segments:
        session.add(
            TimelineSegment(
                file_id=segment.file_id,
                day=segment.day,
                segment_start_at=segment.segment_start_at.isoformat(),
                segment_end_at=segment.segment_end_at.isoformat(),
                duration_sec=segment.duration_sec,
                playback_url=segment.playback_url,
                file_offset_sec=segment.file_offset_sec,
                prev_gap_sec=segment.prev_gap_sec,
                next_gap_sec=segment.next_gap_sec,
                status=segment.status,
            )
        )

    upsert_day_summary(session, day, build_result.summary)
    session.flush()
    return build_result


def rebuild_impacted_days(session: Session, file_record: VideoFile) -> None:
    for day in collect_impacted_days(file_record):
        rebuild_day_timeline(session, day)
