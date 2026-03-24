from __future__ import annotations

import json
from datetime import datetime
from zoneinfo import ZoneInfo

from sqlalchemy import asc, desc
from sqlalchemy.orm import Session

from app.models import TimelineSegment, VideoFile
from app.services.timeline_builder import WARNING_GAP_SEC


def _normalize_datetime(value: datetime, timezone_name: str) -> datetime:
    if value.tzinfo is not None:
        return value
    return value.replace(tzinfo=ZoneInfo(timezone_name))


def _parse_issue_flags(raw_issue_flags: str | None) -> list[str]:
    if not raw_issue_flags:
        return []
    try:
        parsed = json.loads(raw_issue_flags)
    except json.JSONDecodeError:
        return []
    if not isinstance(parsed, list):
        return []
    return [str(item) for item in parsed]


def _build_issue_flags(segment: TimelineSegment, file_record: VideoFile) -> list[str]:
    issue_flags = _parse_issue_flags(file_record.issue_flags)
    if segment.prev_gap_sec is not None:
        if segment.prev_gap_sec > WARNING_GAP_SEC:
            issue_flags.append("gap_before")
        elif segment.prev_gap_sec < 0:
            issue_flags.append("overlap_before")
    return list(dict.fromkeys(issue_flags))


def _build_segment_payload(segment: TimelineSegment, file_record: VideoFile) -> dict[str, object]:
    return {
        "id": segment.id,
        "fileId": segment.file_id,
        "startAt": segment.segment_start_at,
        "endAt": segment.segment_end_at,
        "durationSec": float(segment.duration_sec),
        "playbackUrl": segment.playback_url,
        "fileOffsetSec": float(segment.file_offset_sec),
        "status": segment.status,
        "issueFlags": _build_issue_flags(segment, file_record),
    }


def _segment_query(session: Session):
    return session.query(TimelineSegment, VideoFile).join(
        VideoFile, VideoFile.id == TimelineSegment.file_id
    )


def locate_at(
    session: Session,
    at: datetime,
    *,
    timezone_name: str = "Asia/Shanghai",
) -> dict[str, object]:
    normalized_at = _normalize_datetime(at, timezone_name)
    at_iso = normalized_at.isoformat()

    current = (
        _segment_query(session)
        .filter(TimelineSegment.segment_start_at <= at_iso)
        .filter(TimelineSegment.segment_end_at > at_iso)
        .order_by(desc(TimelineSegment.segment_start_at), desc(TimelineSegment.id))
        .first()
    )
    if current is not None:
        segment, file_record = current
        segment_start_at = datetime.fromisoformat(segment.segment_start_at)
        seek_offset_sec = float(segment.file_offset_sec) + (
            normalized_at - segment_start_at
        ).total_seconds()
        return {
            "found": True,
            "segment": _build_segment_payload(segment, file_record),
            "seekOffsetSec": seek_offset_sec,
            "gap": None,
            "nextSegment": None,
        }

    previous = (
        _segment_query(session)
        .filter(TimelineSegment.segment_end_at <= at_iso)
        .order_by(desc(TimelineSegment.segment_end_at), desc(TimelineSegment.id))
        .first()
    )
    next_segment = (
        _segment_query(session)
        .filter(TimelineSegment.segment_start_at > at_iso)
        .order_by(asc(TimelineSegment.segment_start_at), asc(TimelineSegment.id))
        .first()
    )

    gap_start_at = previous[0].segment_end_at if previous is not None else at_iso
    gap_end_at = next_segment[0].segment_start_at if next_segment is not None else at_iso

    return {
        "found": False,
        "segment": None,
        "seekOffsetSec": None,
        "gap": {
            "startAt": gap_start_at,
            "endAt": gap_end_at,
        },
        "nextSegment": (
            _build_segment_payload(next_segment[0], next_segment[1])
            if next_segment is not None
            else None
        ),
    }
