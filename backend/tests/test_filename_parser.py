from __future__ import annotations

import pytest

from app.services.filename_parser import parse_camera_filename


def test_parse_camera_filename():
    parsed = parse_camera_filename("00_20260318015937_20260318021002.mp4")
    assert parsed.name_start_at.isoformat() == "2026-03-18T01:59:37+08:00"
    assert parsed.name_end_at.isoformat() == "2026-03-18T02:10:02+08:00"


def test_parse_invalid_camera_filename():
    with pytest.raises(ValueError):
        parse_camera_filename("broken-name.mp4")


def test_parse_camera_filename_rejects_start_after_end():
    with pytest.raises(ValueError):
        parse_camera_filename("00_20260318021002_20260318015937.mp4")


def test_parse_invalid_calendar_time():
    with pytest.raises(ValueError):
        parse_camera_filename("00_20260230000000_20260230010000.mp4")


def test_parse_cross_day_camera_filename():
    parsed = parse_camera_filename("00_20260331235900_20260401001000.mp4")
    assert parsed.name_start_at.isoformat() == "2026-03-31T23:59:00+08:00"
    assert parsed.name_end_at.isoformat() == "2026-04-01T00:10:00+08:00"
