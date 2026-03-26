from app.models import DaySummary, TimelineSegment, VideoFile


def _make_video_file(
    *,
    file_id: int,
    camera_no: int = 1,
    status: str,
    issue_flags: str,
) -> VideoFile:
    return VideoFile(
        id=file_id,
        camera_no=camera_no,
        file_path=f"/videos/{file_id}.mp4",
        file_name=f"{file_id}.mp4",
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
        status=status,
        issue_flags=issue_flags,
        created_at="2026-03-24T00:00:00+08:00",
        updated_at="2026-03-24T00:00:00+08:00",
    )


def test_get_timeline_returns_summary_segments_and_gaps(
    authenticated_client, sqlite_session
):
    sqlite_session.add_all(
        [
            _make_video_file(file_id=11, status="ready", issue_flags="[]"),
            _make_video_file(
                file_id=12,
                status="warning",
                issue_flags='["duration_mismatch"]',
            ),
            TimelineSegment(
                id=201,
                file_id=11,
                camera_no=1,
                day="2026-03-17",
                segment_start_at="2026-03-17T00:00:00+08:00",
                segment_end_at="2026-03-17T00:05:00+08:00",
                duration_sec=300.0,
                playback_url="/api/videos/11/stream",
                file_offset_sec=0.0,
                prev_gap_sec=None,
                next_gap_sec=40.0,
                status="ready",
            ),
            TimelineSegment(
                id=202,
                file_id=12,
                camera_no=1,
                day="2026-03-17",
                segment_start_at="2026-03-17T00:05:40+08:00",
                segment_end_at="2026-03-17T00:10:45+08:00",
                duration_sec=305.0,
                playback_url="/api/videos/12/stream",
                file_offset_sec=0.0,
                prev_gap_sec=40.0,
                next_gap_sec=None,
                status="warning",
            ),
            DaySummary(
                camera_no=1,
                day="2026-03-17",
                first_segment_at="2026-03-17T00:00:00+08:00",
                last_segment_at="2026-03-17T00:10:45+08:00",
                total_segment_count=2,
                total_recorded_sec=605.0,
                total_gap_sec=40.0,
                has_warning=True,
                updated_at="2026-03-24T00:00:00+08:00",
            ),
        ]
    )
    sqlite_session.commit()

    response = authenticated_client.get(
        "/api/timeline", params={"camera": 1, "day": "2026-03-17"}
    )

    assert response.status_code == 200
    assert response.json() == {
        "day": "2026-03-17",
        "timezone": "Asia/Shanghai",
        "summary": {
            "segmentCount": 2,
            "recordedSeconds": 605.0,
            "gapSeconds": 40.0,
            "warningCount": 1,
        },
        "segments": [
            {
                "id": 201,
                "fileId": 11,
                "startAt": "2026-03-17T00:00:00+08:00",
                "endAt": "2026-03-17T00:05:00+08:00",
                "durationSec": 300.0,
                "playbackUrl": "/api/videos/11/stream",
                "fileOffsetSec": 0.0,
                "status": "ready",
                "issueFlags": [],
            },
            {
                "id": 202,
                "fileId": 12,
                "startAt": "2026-03-17T00:05:40+08:00",
                "endAt": "2026-03-17T00:10:45+08:00",
                "durationSec": 305.0,
                "playbackUrl": "/api/videos/12/stream",
                "fileOffsetSec": 0.0,
                "status": "warning",
                "issueFlags": ["duration_mismatch", "gap_before"],
            },
        ],
        "gaps": [
            {
                "startAt": "2026-03-17T00:05:00+08:00",
                "endAt": "2026-03-17T00:05:40+08:00",
                "durationSec": 40.0,
            }
        ],
    }


def test_get_timeline_returns_404_when_day_missing(authenticated_client):
    response = authenticated_client.get(
        "/api/timeline", params={"camera": 1, "day": "2026-03-19"}
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "timeline not found"}


def test_get_timeline_omits_small_continuous_gap_from_gaps(
    authenticated_client, sqlite_session
):
    sqlite_session.add_all(
        [
            _make_video_file(file_id=21, status="ready", issue_flags="[]"),
            _make_video_file(file_id=22, status="ready", issue_flags="[]"),
            TimelineSegment(
                id=211,
                file_id=21,
                camera_no=1,
                day="2026-03-18",
                segment_start_at="2026-03-18T00:00:00+08:00",
                segment_end_at="2026-03-18T00:05:00+08:00",
                duration_sec=300.0,
                playback_url="/api/videos/21/stream",
                file_offset_sec=0.0,
                prev_gap_sec=None,
                next_gap_sec=0.0,
                status="ready",
            ),
            TimelineSegment(
                id=212,
                file_id=22,
                camera_no=1,
                day="2026-03-18",
                segment_start_at="2026-03-18T00:05:01.500000+08:00",
                segment_end_at="2026-03-18T00:10:01.500000+08:00",
                duration_sec=300.0,
                playback_url="/api/videos/22/stream",
                file_offset_sec=0.0,
                prev_gap_sec=0.0,
                next_gap_sec=None,
                status="ready",
            ),
            DaySummary(
                camera_no=1,
                day="2026-03-18",
                first_segment_at="2026-03-18T00:00:00+08:00",
                last_segment_at="2026-03-18T00:10:01.500000+08:00",
                total_segment_count=2,
                total_recorded_sec=600.0,
                total_gap_sec=0.0,
                has_warning=False,
                updated_at="2026-03-24T00:00:00+08:00",
            ),
        ]
    )
    sqlite_session.commit()

    response = authenticated_client.get(
        "/api/timeline", params={"camera": 1, "day": "2026-03-18"}
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["summary"]["gapSeconds"] == 0.0
    assert payload["gaps"] == []


def test_timeline_returns_404_for_unknown_camera(authenticated_client):
    response = authenticated_client.get(
        "/api/timeline", params={"camera": 99, "day": "2026-03-18"}
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "camera not found"}


def test_timeline_filters_segments_by_camera(authenticated_client, sqlite_session):
    sqlite_session.add_all(
        [
            _make_video_file(file_id=31, status="ready", issue_flags="[]"),
            _make_video_file(file_id=32, camera_no=2, status="ready", issue_flags="[]"),
            TimelineSegment(
                id=311,
                file_id=31,
                camera_no=1,
                day="2026-03-18",
                segment_start_at="2026-03-18T00:00:00+08:00",
                segment_end_at="2026-03-18T00:05:00+08:00",
                duration_sec=300.0,
                playback_url="/api/videos/31/stream",
                file_offset_sec=0.0,
                prev_gap_sec=None,
                next_gap_sec=None,
                status="ready",
            ),
            TimelineSegment(
                id=312,
                file_id=32,
                camera_no=2,
                day="2026-03-18",
                segment_start_at="2026-03-18T01:00:00+08:00",
                segment_end_at="2026-03-18T01:05:00+08:00",
                duration_sec=300.0,
                playback_url="/api/videos/32/stream",
                file_offset_sec=0.0,
                prev_gap_sec=None,
                next_gap_sec=None,
                status="ready",
            ),
            DaySummary(
                camera_no=1,
                day="2026-03-18",
                first_segment_at="2026-03-18T00:00:00+08:00",
                last_segment_at="2026-03-18T00:05:00+08:00",
                total_segment_count=1,
                total_recorded_sec=300.0,
                total_gap_sec=0.0,
                has_warning=False,
                updated_at="2026-03-24T00:00:00+08:00",
            ),
            DaySummary(
                camera_no=2,
                day="2026-03-18",
                first_segment_at="2026-03-18T01:00:00+08:00",
                last_segment_at="2026-03-18T01:05:00+08:00",
                total_segment_count=1,
                total_recorded_sec=300.0,
                total_gap_sec=0.0,
                has_warning=False,
                updated_at="2026-03-24T00:00:00+08:00",
            ),
        ]
    )
    sqlite_session.commit()

    response = authenticated_client.get(
        "/api/timeline", params={"camera": 2, "day": "2026-03-18"}
    )

    assert response.status_code == 200
    assert response.json()["segments"] == [
        {
            "id": 312,
            "fileId": 32,
            "startAt": "2026-03-18T01:00:00+08:00",
            "endAt": "2026-03-18T01:05:00+08:00",
            "durationSec": 300.0,
            "playbackUrl": "/api/videos/32/stream",
            "fileOffsetSec": 0.0,
            "status": "ready",
            "issueFlags": [],
        }
    ]
