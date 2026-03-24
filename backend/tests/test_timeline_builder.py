from __future__ import annotations

from app.services.filename_parser import parse_camera_filename
from app.services.timeline_builder import (
    TimelineSourceFile,
    build_day_timeline,
    split_file_ranges_by_day,
)


def _make_source_file(
    *,
    file_id: int,
    file_name: str,
    probe_duration_sec: float,
    playback_url: str | None = None,
) -> TimelineSourceFile:
    parsed = parse_camera_filename(file_name)
    return TimelineSourceFile(
        file_id=file_id,
        file_name=file_name,
        playback_url=playback_url or f"/api/files/{file_id}/play",
        name_start_at=parsed.name_start_at,
        name_end_at=parsed.name_end_at,
        probe_duration_sec=probe_duration_sec,
    )


def test_build_timeline_marks_small_gap_as_continuous():
    file_records = [
        _make_source_file(
            file_id=1,
            file_name="00_20260317000000_20260317001000.mp4",
            probe_duration_sec=600.0,
        ),
        _make_source_file(
            file_id=2,
            file_name="00_20260317001001_20260317002001.mp4",
            probe_duration_sec=600.0,
        ),
    ]

    day_ranges = []
    for file_record in file_records:
        day_ranges.extend(split_file_ranges_by_day(file_record))

    result = build_day_timeline(day_ranges)

    assert len(result.segments) == 2
    assert result.gaps == []
    assert result.segments[0].next_gap_sec == 0.0
    assert result.segments[1].prev_gap_sec == 0.0
    assert result.summary.first_segment_at.isoformat() == "2026-03-17T00:00:00+08:00"
    assert result.summary.last_segment_at.isoformat() == "2026-03-17T00:20:01+08:00"
    assert result.summary.total_recorded_sec == 1200.0
    assert result.summary.total_gap_sec == 0.0
    assert result.summary.total_segment_count == 2
    assert result.summary.has_warning is False


def test_build_timeline_splits_cross_day_file():
    file_record = _make_source_file(
        file_id=10,
        file_name="00_20260317235930_20260318000100.mp4",
        probe_duration_sec=90.0,
    )

    result = split_file_ranges_by_day(file_record)

    assert {item.day for item in result} == {"2026-03-17", "2026-03-18"}
    assert result[0].segment_start_at.isoformat() == "2026-03-17T23:59:30+08:00"
    assert result[0].segment_end_at.isoformat() == "2026-03-18T00:00:00+08:00"
    assert result[0].duration_sec == 30.0
    assert result[0].file_offset_sec == 0.0
    assert result[1].segment_start_at.isoformat() == "2026-03-18T00:00:00+08:00"
    assert result[1].segment_end_at.isoformat() == "2026-03-18T00:01:00+08:00"
    assert result[1].duration_sec == 60.0
    assert result[1].file_offset_sec == 30.0


def test_build_timeline_marks_large_gap_and_duration_mismatch_as_warning():
    file_records = [
        _make_source_file(
            file_id=1,
            file_name="00_20260317000000_20260317000500.mp4",
            probe_duration_sec=300.0,
        ),
        _make_source_file(
            file_id=2,
            file_name="00_20260317000540_20260317001040.mp4",
            probe_duration_sec=305.0,
        ),
    ]

    day_ranges = []
    for file_record in file_records:
        day_ranges.extend(split_file_ranges_by_day(file_record))

    result = build_day_timeline(day_ranges)

    assert len(result.gaps) == 1
    assert result.gaps[0].gap_sec == 40.0
    assert result.gaps[0].gap_start_at.isoformat() == "2026-03-17T00:05:00+08:00"
    assert result.gaps[0].gap_end_at.isoformat() == "2026-03-17T00:05:40+08:00"
    assert result.segments[1].prev_gap_sec == 40.0
    assert result.segments[1].status == "warning"
    assert result.segments[1].issue_flags == ["duration_mismatch", "gap_before"]
    assert result.summary.last_segment_at.isoformat() == "2026-03-17T00:10:45+08:00"
    assert result.summary.total_gap_sec == 40.0
    assert result.summary.has_warning is True


def test_build_timeline_marks_overlap_as_warning():
    file_records = [
        _make_source_file(
            file_id=1,
            file_name="00_20260317000000_20260317000500.mp4",
            probe_duration_sec=300.0,
        ),
        _make_source_file(
            file_id=2,
            file_name="00_20260317000455_20260317000955.mp4",
            probe_duration_sec=300.0,
        ),
    ]

    day_ranges = []
    for file_record in file_records:
        day_ranges.extend(split_file_ranges_by_day(file_record))

    result = build_day_timeline(day_ranges)

    assert result.gaps == []
    assert result.segments[1].prev_gap_sec == -5.0
    assert result.segments[1].status == "warning"
    assert result.segments[1].issue_flags == ["overlap_before"]
    assert result.summary.total_gap_sec == 0.0
    assert result.summary.total_recorded_sec == 600.0
    assert result.summary.has_warning is True
