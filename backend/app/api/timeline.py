from __future__ import annotations

import json
from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.auth import require_authenticated
from app.core.config import Settings, get_settings
from app.core.db import get_db
from app.models import DaySummary, TimelineSegment, VideoFile
from app.schemas.timeline import (
    TimelineGapItem,
    TimelineResponse,
    TimelineSegmentItem,
    TimelineSummary,
)
from app.services.timeline_builder import WARNING_GAP_SEC, is_effective_gap

router = APIRouter(dependencies=[Depends(require_authenticated)])


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


def _build_segment_item(
    segment: TimelineSegment,
    file_record: VideoFile,
) -> TimelineSegmentItem:
    return TimelineSegmentItem(
        id=segment.id,
        fileId=segment.file_id,
        startAt=segment.segment_start_at,
        endAt=segment.segment_end_at,
        durationSec=float(segment.duration_sec),
        playbackUrl=segment.playback_url,
        fileOffsetSec=float(segment.file_offset_sec),
        status=segment.status,
        issueFlags=_build_issue_flags(segment, file_record),
    )


@router.get("/api/timeline", response_model=TimelineResponse)
def get_timeline(
    camera: int,
    day: date,
    session: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> TimelineResponse:
    configured_cameras = {item.camera_no for item in settings.camera_roots}
    if camera not in configured_cameras:
        raise HTTPException(status_code=404, detail="camera not found")

    day_value = day.isoformat()
    summary = (
        session.query(DaySummary)
        .filter(DaySummary.camera_no == camera, DaySummary.day == day_value)
        .one_or_none()
    )
    rows = (
        session.query(TimelineSegment, VideoFile)
        .join(VideoFile, VideoFile.id == TimelineSegment.file_id)
        .filter(TimelineSegment.camera_no == camera, TimelineSegment.day == day_value)
        .filter(VideoFile.camera_no == camera)
        .order_by(
            TimelineSegment.segment_start_at.asc(),
            TimelineSegment.segment_end_at.asc(),
            TimelineSegment.id.asc(),
        )
        .all()
    )

    if summary is None and not rows:
        raise HTTPException(status_code=404, detail="timeline not found")

    segments = [_build_segment_item(segment, file_record) for segment, file_record in rows]

    gaps: list[TimelineGapItem] = []
    for previous, current in zip(rows, rows[1:]):
        previous_segment = previous[0]
        current_segment = current[0]
        gap_sec = (
            datetime.fromisoformat(current_segment.segment_start_at)
            - datetime.fromisoformat(previous_segment.segment_end_at)
        ).total_seconds()
        if is_effective_gap(gap_sec):
            gaps.append(
                TimelineGapItem(
                    startAt=previous_segment.segment_end_at,
                    endAt=current_segment.segment_start_at,
                    durationSec=gap_sec,
                )
            )

    warning_count = sum(1 for segment, _ in rows if segment.status == "warning")

    if summary is None:
        segment_count = len(segments)
        recorded_seconds = sum(item.durationSec for item in segments)
        gap_seconds = sum(item.durationSec for item in gaps)
    else:
        segment_count = summary.total_segment_count
        recorded_seconds = float(summary.total_recorded_sec)
        gap_seconds = float(summary.total_gap_sec)

    return TimelineResponse(
        day=day_value,
        timezone=settings.timezone,
        summary=TimelineSummary(
            segmentCount=segment_count,
            recordedSeconds=recorded_seconds,
            gapSeconds=gap_seconds,
            warningCount=warning_count,
        ),
        segments=segments,
        gaps=gaps,
    )
