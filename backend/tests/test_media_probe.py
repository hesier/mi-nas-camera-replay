from __future__ import annotations

import json
import subprocess
from typing import Any

import pytest

from app.services.media_probe import FFPROBE_TIMEOUT_SEC, parse_probe_payload, probe_media


def test_parse_ffprobe_json():
    payload = {"format": {"duration": "625.0", "start_time": "0.0"}}
    result = parse_probe_payload(payload)
    assert result.duration_sec == 625.0
    assert result.start_time_sec == 0.0


def test_parse_ffprobe_missing_duration():
    with pytest.raises(ValueError):
        parse_probe_payload({"format": {}})


def test_parse_ffprobe_invalid_format_payload():
    with pytest.raises(ValueError):
        parse_probe_payload({"format": "invalid"})


def test_parse_ffprobe_start_time_defaults_to_zero():
    result = parse_probe_payload({"format": {"duration": "12.5"}})
    assert result.start_time_sec == 0.0


def test_parse_ffprobe_invalid_start_time():
    with pytest.raises(ValueError):
        parse_probe_payload({"format": {"duration": "10.0", "start_time": "oops"}})


@pytest.mark.parametrize("duration", ["nan", "-1"])
def test_parse_ffprobe_invalid_duration(duration: str):
    with pytest.raises(ValueError):
        parse_probe_payload({"format": {"duration": duration, "start_time": "0.0"}})


def test_parse_ffprobe_rejects_infinite_start_time():
    with pytest.raises(ValueError):
        parse_probe_payload({"format": {"duration": "10.0", "start_time": "inf"}})


def test_probe_media_invokes_ffprobe(monkeypatch: pytest.MonkeyPatch):
    captured_cmd: list[str] = []
    captured_timeout: float | None = None

    def fake_run(cmd: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        nonlocal captured_timeout
        captured_cmd.extend(cmd)
        captured_timeout = kwargs.get("timeout")
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
    assert captured_timeout == FFPROBE_TIMEOUT_SEC
    assert result.duration_sec == 10.5
    assert result.start_time_sec == 1.25


def test_probe_media_invalid_json(monkeypatch: pytest.MonkeyPatch):
    def fake_run(_: list[str], **__: Any) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout="{not-json",
            stderr="",
        )

    monkeypatch.setattr(subprocess, "run", fake_run)

    with pytest.raises(ValueError):
        probe_media("/tmp/demo.mp4")


def test_probe_media_subprocess_error(monkeypatch: pytest.MonkeyPatch):
    def fake_run(cmd: list[str], **__: Any) -> subprocess.CompletedProcess[str]:
        raise subprocess.TimeoutExpired(cmd=cmd, timeout=1.0)

    monkeypatch.setattr(subprocess, "run", fake_run)

    with pytest.raises(ValueError):
        probe_media("/tmp/demo.mp4")
