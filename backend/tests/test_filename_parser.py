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
