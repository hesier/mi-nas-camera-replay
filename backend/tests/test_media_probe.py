from __future__ import annotations

import json
import subprocess
from typing import Any

import pytest

from app.services.media_probe import parse_probe_payload, probe_media


def test_parse_ffprobe_json():
    payload = {"format": {"duration": "625.0", "start_time": "0.0"}}
    result = parse_probe_payload(payload)
    assert result.duration_sec == 625.0
    assert result.start_time_sec == 0.0


def test_parse_ffprobe_missing_duration():
    with pytest.raises(ValueError):
        parse_probe_payload({"format": {}})


def test_probe_media_invokes_ffprobe(monkeypatch: pytest.MonkeyPatch):
    captured_cmd: list[str] = []

    def fake_run(cmd: list[str], **_: Any) -> subprocess.CompletedProcess[str]:
        captured_cmd.extend(cmd)
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=0,
            stdout=json.dumps({"format": {"duration": "10.5", "start_time": "1.25"}}),
            stderr="",
        )

    monkeypatch.setattr(subprocess, "run", fake_run)

    result = probe_media("/tmp/demo.mp4")

    assert captured_cmd == [
        "ffprobe",
        "-v",
        "error",
        "-print_format",
        "json",
        "-show_format",
        "-show_streams",
        "/tmp/demo.mp4",
    ]
    assert result.duration_sec == 10.5
    assert result.start_time_sec == 1.25
