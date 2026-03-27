from datetime import datetime

from app.models import TimelineSegment, VideoFile
from app.services.locate_service import locate_at


def _make_video_file(
    file_id: int,
    issue_flags: str = "[]",
    *,
    camera_no: int = 1,
) -> VideoFile:
    return VideoFile(
        id=file_id,
        camera_no=camera_no,
        file_path=f"/videos/{file_id}.mp4",
        file_name=f"{file_id}.mp4",
        file_size=1,
        file_mtime=1711209600,
        name_start_at="2026-03-18T00:00:00+08:00",
        name_end_at="2026-03-18T00:10:00+08:00",
        probe_duration_sec=600.0,
        probe_video_codec=None,
        probe_audio_codec=None,
        probe_width=None,
        probe_height=None,
        probe_start_time_sec=0.0,
        actual_start_at="2026-03-18T00:00:00+08:00",
        actual_end_at="2026-03-18T00:10:00+08:00",
        time_source="filename",
        status="ready",
        issue_flags=issue_flags,
        created_at="2026-03-24T00:00:00+08:00",
        updated_at="2026-03-24T00:00:00+08:00",
    )


def test_locate_at_returns_found_segment_with_seek_offset(sqlite_session):
    sqlite_session.add(_make_video_file(51, '["duration_mismatch"]'))
    sqlite_session.add(
        TimelineSegment(
            id=501,
            file_id=51,
            day="2026-03-18",
            segment_start_at="2026-03-18T00:00:00+08:00",
            segment_end_at="2026-03-18T00:01:00+08:00",
            duration_sec=60.0,
            playback_url="/api/videos/51/stream",
            file_offset_sec=30.0,
            prev_gap_sec=None,
            next_gap_sec=None,
            status="warning",
        )
    )
    sqlite_session.commit()

    result = locate_at(sqlite_session, datetime.fromisoformat("2026-03-18T00:00:15"))

    assert result["found"] is True
    assert result["seekOffsetSec"] == 45.0
    assert result["segment"]["id"] == 501
    assert result["segment"]["issueFlags"] == ["duration_mismatch"]


def test_locate_at_returns_gap_and_next_segment(sqlite_session):
    sqlite_session.add_all([_make_video_file(61), _make_video_file(62)])
    sqlite_session.add_all(
        [
            TimelineSegment(
                id=601,
                file_id=61,
                day="2026-03-18",
                segment_start_at="2026-03-18T00:00:00+08:00",
                segment_end_at="2026-03-18T00:05:00+08:00",
                duration_sec=300.0,
                playback_url="/api/videos/61/stream",
                file_offset_sec=0.0,
                prev_gap_sec=None,
                next_gap_sec=40.0,
                status="ready",
            ),
            TimelineSegment(
                id=602,
                file_id=62,
                day="2026-03-18",
                segment_start_at="2026-03-18T00:05:40+08:00",
                segment_end_at="2026-03-18T00:10:40+08:00",
                duration_sec=300.0,
                playback_url="/api/videos/62/stream",
                file_offset_sec=0.0,
                prev_gap_sec=40.0,
                next_gap_sec=None,
                status="ready",
            ),
        ]
    )
    sqlite_session.commit()

    result = locate_at(sqlite_session, datetime.fromisoformat("2026-03-18T00:05:20"))

    assert result["found"] is False
    assert result["gap"] == {
        "startAt": "2026-03-18T00:05:00+08:00",
        "endAt": "2026-03-18T00:05:40+08:00",
    }
    assert result["nextSegment"]["id"] == 602
    assert result["nextSegment"]["issueFlags"] == ["gap_before"]


def test_locate_at_treats_equivalent_instants_with_different_offsets_as_same(
    sqlite_session,
):
    sqlite_session.add(_make_video_file(71))
    sqlite_session.add(
        TimelineSegment(
            id=701,
            file_id=71,
            day="2026-03-18",
            segment_start_at="2026-03-18T00:00:00+08:00",
            segment_end_at="2026-03-18T00:01:00+08:00",
            duration_sec=60.0,
            playback_url="/api/videos/71/stream",
            file_offset_sec=10.0,
            prev_gap_sec=None,
            next_gap_sec=None,
            status="ready",
        )
    )
    sqlite_session.commit()

    shanghai_result = locate_at(
        sqlite_session,
        datetime.fromisoformat("2026-03-18T00:00:15+08:00"),
    )
    utc_result = locate_at(
        sqlite_session,
        datetime.fromisoformat("2026-03-17T16:00:15+00:00"),
    )

    assert shanghai_result == utc_result
    assert shanghai_result["found"] is True
    assert shanghai_result["segment"]["id"] == 701
    assert shanghai_result["seekOffsetSec"] == 25.0


def test_locate_at_treats_small_continuous_gap_as_next_segment(sqlite_session):
    sqlite_session.add_all([_make_video_file(81), _make_video_file(82)])
    sqlite_session.add_all(
        [
            TimelineSegment(
                id=801,
                file_id=81,
                day="2026-03-18",
                segment_start_at="2026-03-18T00:00:00+08:00",
                segment_end_at="2026-03-18T00:05:00+08:00",
                duration_sec=300.0,
                playback_url="/api/videos/81/stream",
                file_offset_sec=0.0,
                prev_gap_sec=None,
                next_gap_sec=1.5,
                status="ready",
            ),
            TimelineSegment(
                id=802,
                file_id=82,
                day="2026-03-18",
                segment_start_at="2026-03-18T00:05:01.500000+08:00",
                segment_end_at="2026-03-18T00:10:01.500000+08:00",
                duration_sec=300.0,
                playback_url="/api/videos/82/stream",
                file_offset_sec=12.0,
                prev_gap_sec=0.0,
                next_gap_sec=None,
                status="ready",
            ),
        ]
    )
    sqlite_session.commit()

    result = locate_at(sqlite_session, datetime.fromisoformat("2026-03-18T00:05:00.800000"))

    assert result["found"] is True
    assert result["segment"]["id"] == 802
    assert result["seekOffsetSec"] == 12.0
    assert result["gap"] is None
    assert result["nextSegment"] is None


def test_locate_at_keeps_subsecond_precision_when_time_is_inside_segment(sqlite_session):
    sqlite_session.add_all([_make_video_file(91), _make_video_file(92)])
    sqlite_session.add_all(
        [
            TimelineSegment(
                id=901,
                file_id=91,
                day="2026-03-18",
                segment_start_at="2026-03-18T00:00:00+08:00",
                segment_end_at="2026-03-18T00:05:00+08:00",
                duration_sec=300.0,
                playback_url="/api/videos/91/stream",
                file_offset_sec=0.0,
                prev_gap_sec=None,
                next_gap_sec=0.5,
                status="ready",
            ),
            TimelineSegment(
                id=902,
                file_id=92,
                day="2026-03-18",
                segment_start_at="2026-03-18T00:05:00.500000+08:00",
                segment_end_at="2026-03-18T00:10:00.500000+08:00",
                duration_sec=300.0,
                playback_url="/api/videos/92/stream",
                file_offset_sec=12.0,
                prev_gap_sec=0.0,
                next_gap_sec=None,
                status="ready",
            ),
        ]
    )
    sqlite_session.commit()

    result = locate_at(sqlite_session, datetime.fromisoformat("2026-03-18T00:05:00.800000"))

    assert result["found"] is True
    assert result["segment"]["id"] == 902
    assert result["seekOffsetSec"] == 12.3
    assert result["gap"] is None
    assert result["nextSegment"] is None


def test_locate_at_filters_segments_by_camera(sqlite_session):
    sqlite_session.add_all(
        [
            _make_video_file(101, camera_no=1),
            _make_video_file(102, camera_no=2),
            TimelineSegment(
                id=1001,
                file_id=101,
                camera_no=1,
                day="2026-03-18",
                segment_start_at="2026-03-18T00:00:00+08:00",
                segment_end_at="2026-03-18T00:01:00+08:00",
                duration_sec=60.0,
                playback_url="/api/videos/101/stream",
                file_offset_sec=10.0,
                prev_gap_sec=None,
                next_gap_sec=None,
                status="ready",
            ),
            TimelineSegment(
                id=1002,
                file_id=102,
                camera_no=2,
                day="2026-03-18",
                segment_start_at="2026-03-18T00:00:00+08:00",
                segment_end_at="2026-03-18T00:01:00+08:00",
                duration_sec=60.0,
                playback_url="/api/videos/102/stream",
                file_offset_sec=20.0,
                prev_gap_sec=None,
                next_gap_sec=None,
                status="ready",
            ),
        ]
    )
    sqlite_session.commit()

    result = locate_at(
        sqlite_session,
        datetime.fromisoformat("2026-03-18T00:00:15"),
        camera_no=2,
    )

    assert result["found"] is True
    assert result["segment"]["id"] == 1002
    assert result["segment"]["fileId"] == 102
    assert result["seekOffsetSec"] == 35.0
