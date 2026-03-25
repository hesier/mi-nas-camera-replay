from app.models import VideoFile


def _make_video_file(file_id: int, file_path: str, file_size: int) -> VideoFile:
    return VideoFile(
        id=file_id,
        file_path=file_path,
        file_name="sample.mp4",
        file_size=file_size,
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


def test_video_stream_returns_full_file_when_range_header_missing(
    client,
    sqlite_session,
    tmp_path,
):
    file_path = tmp_path / "sample.mp4"
    content = b"0123456789"
    file_path.write_bytes(content)
    sqlite_session.add(_make_video_file(101, str(file_path), len(content)))
    sqlite_session.commit()

    response = client.get("/api/videos/101/stream")

    assert response.status_code == 200
    assert response.content == content
    assert response.headers["accept-ranges"] == "bytes"
    assert response.headers["content-length"] == str(len(content))
    assert response.headers["content-type"] == "video/mp4"


def test_video_stream_supports_explicit_byte_range(client, sqlite_session, tmp_path):
    file_path = tmp_path / "sample.mp4"
    content = b"abcdefghijklmnopqrstuvwxyz"
    file_path.write_bytes(content)
    sqlite_session.add(_make_video_file(102, str(file_path), len(content)))
    sqlite_session.commit()

    response = client.get(
        "/api/videos/102/stream",
        headers={"Range": "bytes=5-9"},
    )

    assert response.status_code == 206
    assert response.content == b"fghij"
    assert response.headers["accept-ranges"] == "bytes"
    assert response.headers["content-length"] == "5"
    assert response.headers["content-range"] == "bytes 5-9/26"
    assert response.headers["content-type"] == "video/mp4"


def test_video_stream_returns_416_for_invalid_range(client, sqlite_session, tmp_path):
    file_path = tmp_path / "sample.mp4"
    content = b"0123456789"
    file_path.write_bytes(content)
    sqlite_session.add(_make_video_file(103, str(file_path), len(content)))
    sqlite_session.commit()

    response = client.get(
        "/api/videos/103/stream",
        headers={"Range": "bytes=20-30"},
    )

    assert response.status_code == 416
    assert response.json() == {"detail": "invalid range"}
    assert response.headers["content-range"] == "bytes */10"


def test_video_stream_returns_404_when_file_record_missing(client):
    response = client.get("/api/videos/999/stream")

    assert response.status_code == 404
    assert response.json() == {"detail": "video not found"}
