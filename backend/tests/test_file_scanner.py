from __future__ import annotations

from app.services.file_scanner import scan_video_files, should_reprobe


def test_scanner_returns_mp4_files(tmp_path):
    (tmp_path / "a.mp4").write_bytes(b"x")
    (tmp_path / "ignore.txt").write_bytes(b"x")

    files = scan_video_files(tmp_path)

    assert [item.name for item in files] == ["a.mp4"]


def test_skip_reprobe_when_size_and_mtime_unchanged(existing_record, incoming_file):
    assert should_reprobe(existing_record, incoming_file) is False


def test_reprobe_when_size_changes(existing_record, incoming_file):
    incoming_file.file_size += 1

    assert should_reprobe(existing_record, incoming_file) is True
