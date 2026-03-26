from app.models import TimelineSegment, VideoFile


def _make_video_file(file_id: int, *, camera_no: int = 1) -> VideoFile:
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
        issue_flags="[]",
        created_at="2026-03-24T00:00:00+08:00",
        updated_at="2026-03-24T00:00:00+08:00",
    )


def test_locate_returns_segment_when_time_hits_recording(
    authenticated_client, sqlite_session
):
    sqlite_session.add(_make_video_file(21))
    sqlite_session.add(
        TimelineSegment(
            id=301,
            file_id=21,
            camera_no=1,
            day="2026-03-18",
            segment_start_at="2026-03-18T00:00:00+08:00",
            segment_end_at="2026-03-18T00:01:00+08:00",
            duration_sec=60.0,
            playback_url="/api/videos/21/stream",
            file_offset_sec=30.0,
            prev_gap_sec=None,
            next_gap_sec=None,
            status="ready",
        )
    )
    sqlite_session.commit()

    response = authenticated_client.get(
        "/api/locate", params={"camera": 1, "at": "2026-03-18T00:00:15"}
    )

    assert response.status_code == 200
    assert response.json() == {
        "found": True,
        "segment": {
            "id": 301,
            "fileId": 21,
            "startAt": "2026-03-18T00:00:00+08:00",
            "endAt": "2026-03-18T00:01:00+08:00",
            "durationSec": 60.0,
            "playbackUrl": "/api/videos/21/stream",
            "fileOffsetSec": 30.0,
            "status": "ready",
            "issueFlags": [],
        },
        "seekOffsetSec": 45.0,
        "gap": None,
        "nextSegment": None,
    }


def test_locate_returns_gap_and_next_segment_when_time_hits_gap(
    authenticated_client, sqlite_session
):
    sqlite_session.add_all([_make_video_file(31), _make_video_file(32)])
    sqlite_session.add_all(
        [
            TimelineSegment(
                id=401,
                file_id=31,
                camera_no=1,
                day="2026-03-18",
                segment_start_at="2026-03-18T00:00:00+08:00",
                segment_end_at="2026-03-18T00:05:00+08:00",
                duration_sec=300.0,
                playback_url="/api/videos/31/stream",
                file_offset_sec=0.0,
                prev_gap_sec=None,
                next_gap_sec=40.0,
                status="ready",
            ),
            TimelineSegment(
                id=402,
                file_id=32,
                camera_no=1,
                day="2026-03-18",
                segment_start_at="2026-03-18T00:05:40+08:00",
                segment_end_at="2026-03-18T00:10:40+08:00",
                duration_sec=300.0,
                playback_url="/api/videos/32/stream",
                file_offset_sec=0.0,
                prev_gap_sec=40.0,
                next_gap_sec=None,
                status="ready",
            ),
        ]
    )
    sqlite_session.commit()

    response = authenticated_client.get(
        "/api/locate", params={"camera": 1, "at": "2026-03-18T00:05:20"}
    )

    assert response.status_code == 200
    assert response.json() == {
        "found": False,
        "segment": None,
        "seekOffsetSec": None,
        "gap": {
            "startAt": "2026-03-18T00:05:00+08:00",
            "endAt": "2026-03-18T00:05:40+08:00",
        },
        "nextSegment": {
            "id": 402,
            "fileId": 32,
            "startAt": "2026-03-18T00:05:40+08:00",
            "endAt": "2026-03-18T00:10:40+08:00",
            "durationSec": 300.0,
            "playbackUrl": "/api/videos/32/stream",
            "fileOffsetSec": 0.0,
            "status": "ready",
            "issueFlags": ["gap_before"],
        },
    }


def test_locate_returns_404_for_unknown_camera(authenticated_client):
    response = authenticated_client.get(
        "/api/locate", params={"camera": 99, "at": "2026-03-18T00:05:20"}
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "camera not found"}


def test_locate_filters_segments_by_camera(authenticated_client, sqlite_session):
    sqlite_session.add_all(
        [
            _make_video_file(41, camera_no=1),
            _make_video_file(42, camera_no=2),
            TimelineSegment(
                id=411,
                file_id=41,
                camera_no=1,
                day="2026-03-18",
                segment_start_at="2026-03-18T00:00:00+08:00",
                segment_end_at="2026-03-18T00:01:00+08:00",
                duration_sec=60.0,
                playback_url="/api/videos/41/stream",
                file_offset_sec=10.0,
                prev_gap_sec=None,
                next_gap_sec=None,
                status="ready",
            ),
            TimelineSegment(
                id=412,
                file_id=42,
                camera_no=2,
                day="2026-03-18",
                segment_start_at="2026-03-18T00:00:00+08:00",
                segment_end_at="2026-03-18T00:01:00+08:00",
                duration_sec=60.0,
                playback_url="/api/videos/42/stream",
                file_offset_sec=20.0,
                prev_gap_sec=None,
                next_gap_sec=None,
                status="ready",
            ),
        ]
    )
    sqlite_session.commit()

    response = authenticated_client.get(
        "/api/locate", params={"camera": 2, "at": "2026-03-18T00:00:15"}
    )

    assert response.status_code == 200
    assert response.json()["segment"]["id"] == 412
    assert response.json()["segment"]["fileId"] == 42
    assert response.json()["seekOffsetSec"] == 35.0
