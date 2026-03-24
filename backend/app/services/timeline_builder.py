from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import dataclass, field, replace
from datetime import datetime, time, timedelta
from typing import Iterable


CONTINUOUS_GAP_SEC = 2.0
WARNING_GAP_SEC = 30.0
DURATION_MISMATCH_SEC = 2.0


@dataclass(frozen=True)
class TimelineSourceFile:
    file_id: int
    file_name: str
    playback_url: str
    name_start_at: datetime
    name_end_at: datetime
    probe_duration_sec: float


@dataclass(frozen=True)
class TimelineDayRange:
    file_id: int
    day: str
    segment_start_at: datetime
    segment_end_at: datetime
    duration_sec: float
    playback_url: str
    file_offset_sec: float
    status: str
    issue_flags: tuple[str, ...] = ()


@dataclass(frozen=True)
class TimelineGap:
    day: str
    gap_start_at: datetime
    gap_end_at: datetime
    gap_sec: float
    previous_file_id: int
    next_file_id: int


@dataclass(frozen=True)
class TimelineSegmentSnapshot:
    file_id: int
    day: str
    segment_start_at: datetime
    segment_end_at: datetime
    duration_sec: float
    playback_url: str
    file_offset_sec: float
    prev_gap_sec: float | None
    next_gap_sec: float | None
    status: str
    issue_flags: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class DaySummarySnapshot:
    first_segment_at: datetime | None
    last_segment_at: datetime | None
    total_recorded_sec: float
    total_gap_sec: float
    has_warning: bool
    total_segment_count: int


@dataclass(frozen=True)
class TimelineBuildResult:
    segments: list[TimelineSegmentSnapshot]
    gaps: list[TimelineGap]
    summary: DaySummarySnapshot


def _normalize_duration(duration_sec: float) -> float:
    try:
        normalized = float(duration_sec)
    except (TypeError, ValueError) as exc:
        raise ValueError("invalid probe duration") from exc
    if (not math.isfinite(normalized)) or normalized < 0:
        raise ValueError("invalid probe duration")
    return normalized


def _build_base_status(source_file: TimelineSourceFile) -> tuple[str, tuple[str, ...]]:
    name_duration = (source_file.name_end_at - source_file.name_start_at).total_seconds()
    duration_diff = abs(name_duration - source_file.probe_duration_sec)
    issue_flags: list[str] = []
    if duration_diff > DURATION_MISMATCH_SEC:
        issue_flags.append("duration_mismatch")
    status = "warning" if duration_diff > DURATION_MISMATCH_SEC else "ready"
    return status, tuple(issue_flags)


def split_file_ranges_by_day(source_file: TimelineSourceFile) -> list[TimelineDayRange]:
    probe_duration_sec = _normalize_duration(source_file.probe_duration_sec)
    actual_start_at = source_file.name_start_at
    actual_end_at = actual_start_at + timedelta(seconds=probe_duration_sec)
    status, issue_flags = _build_base_status(
        replace(source_file, probe_duration_sec=probe_duration_sec)
    )

    current_start = actual_start_at
    file_offset_sec = 0.0
    results: list[TimelineDayRange] = []

    while current_start.date() < actual_end_at.date():
        next_midnight = datetime.combine(
            current_start.date() + timedelta(days=1),
            time.min,
            tzinfo=current_start.tzinfo,
        )
        duration_sec = (next_midnight - current_start).total_seconds()
        results.append(
            TimelineDayRange(
                file_id=source_file.file_id,
                day=current_start.date().isoformat(),
                segment_start_at=current_start,
                segment_end_at=next_midnight,
                duration_sec=duration_sec,
                playback_url=source_file.playback_url,
                file_offset_sec=file_offset_sec,
                status=status,
                issue_flags=issue_flags,
            )
        )
        current_start = next_midnight
        file_offset_sec += duration_sec

    final_duration_sec = (actual_end_at - current_start).total_seconds()
    if final_duration_sec > 0 or not results:
        results.append(
            TimelineDayRange(
                file_id=source_file.file_id,
                day=current_start.date().isoformat(),
                segment_start_at=current_start,
                segment_end_at=actual_end_at,
                duration_sec=final_duration_sec,
                playback_url=source_file.playback_url,
                file_offset_sec=file_offset_sec,
                status=status,
                issue_flags=issue_flags,
            )
        )

    return results


def build_timelines_by_day(
    source_files: Iterable[TimelineSourceFile],
) -> dict[str, TimelineBuildResult]:
    grouped_ranges: dict[str, list[TimelineDayRange]] = defaultdict(list)

    for source_file in source_files:
        for day_range in split_file_ranges_by_day(source_file):
            grouped_ranges[day_range.day].append(day_range)

    return {
        day: build_day_timeline(grouped_ranges[day])
        for day in sorted(grouped_ranges.keys())
    }


def build_day_timeline(day_ranges: Iterable[TimelineDayRange]) -> TimelineBuildResult:
    sorted_ranges = sorted(
        day_ranges,
        key=lambda item: (item.segment_start_at, item.segment_end_at, item.file_id),
    )
    if not sorted_ranges:
        return TimelineBuildResult(
            segments=[],
            gaps=[],
            summary=DaySummarySnapshot(
                first_segment_at=None,
                last_segment_at=None,
                total_recorded_sec=0.0,
                total_gap_sec=0.0,
                has_warning=False,
                total_segment_count=0,
            ),
        )

    days = {item.day for item in sorted_ranges}
    if len(days) != 1:
        raise ValueError("build_day_timeline expects ranges from a single day")

    segments: list[TimelineSegmentSnapshot] = []
    gaps: list[TimelineGap] = []
    total_gap_sec = 0.0

    for item in sorted_ranges:
        issue_flags = list(item.issue_flags)
        prev_gap_sec: float | None = None
        next_gap_sec: float | None = None

        if segments:
            previous_segment = segments[-1]
            gap_sec = (
                item.segment_start_at - previous_segment.segment_end_at
            ).total_seconds()

            if 0 <= gap_sec <= CONTINUOUS_GAP_SEC:
                gap_sec = 0.0
            elif gap_sec > CONTINUOUS_GAP_SEC:
                total_gap_sec += gap_sec
                gaps.append(
                    TimelineGap(
                        day=item.day,
                        gap_start_at=previous_segment.segment_end_at,
                        gap_end_at=item.segment_start_at,
                        gap_sec=gap_sec,
                        previous_file_id=previous_segment.file_id,
                        next_file_id=item.file_id,
                    )
                )
                if gap_sec > WARNING_GAP_SEC:
                    issue_flags.append("gap_before")
            elif gap_sec < 0:
                issue_flags.append("overlap_before")

            prev_gap_sec = gap_sec
            segments[-1] = replace(previous_segment, next_gap_sec=gap_sec)

        deduped_issue_flags = list(dict.fromkeys(issue_flags))
        status = "warning" if deduped_issue_flags else "ready"
        segments.append(
            TimelineSegmentSnapshot(
                file_id=item.file_id,
                day=item.day,
                segment_start_at=item.segment_start_at,
                segment_end_at=item.segment_end_at,
                duration_sec=item.duration_sec,
                playback_url=item.playback_url,
                file_offset_sec=item.file_offset_sec,
                prev_gap_sec=prev_gap_sec,
                next_gap_sec=next_gap_sec,
                status=status,
                issue_flags=deduped_issue_flags,
            )
        )

    first_segment_at = min(segment.segment_start_at for segment in segments)
    last_segment_at = max(segment.segment_end_at for segment in segments)
    total_recorded_sec = sum(segment.duration_sec for segment in segments)
    has_warning = any(segment.status == "warning" for segment in segments)

    return TimelineBuildResult(
        segments=segments,
        gaps=gaps,
        summary=DaySummarySnapshot(
            first_segment_at=first_segment_at,
            last_segment_at=last_segment_at,
            total_recorded_sec=total_recorded_sec,
            total_gap_sec=total_gap_sec,
            has_warning=has_warning,
            total_segment_count=len(segments),
        ),
    )
