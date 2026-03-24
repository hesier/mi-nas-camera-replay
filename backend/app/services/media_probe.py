from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from typing import Any, Mapping


@dataclass(frozen=True)
class ProbeResult:
    duration_sec: float
    start_time_sec: float


def parse_probe_payload(payload: Mapping[str, Any]) -> ProbeResult:
    format_payload = payload.get("format")
    if not isinstance(format_payload, Mapping):
        raise ValueError("invalid ffprobe payload")

    raw_duration = format_payload.get("duration")
    if raw_duration in (None, ""):
        raise ValueError("ffprobe missing duration")

    try:
        duration_sec = float(raw_duration)
    except (TypeError, ValueError) as exc:
        raise ValueError("invalid ffprobe duration") from exc

    raw_start_time = format_payload.get("start_time", 0.0)
    try:
        start_time_sec = float(raw_start_time)
    except (TypeError, ValueError) as exc:
        raise ValueError("invalid ffprobe start_time") from exc

    return ProbeResult(duration_sec=duration_sec, start_time_sec=start_time_sec)


def probe_media(file_path: str) -> ProbeResult:
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-print_format",
        "json",
        "-show_format",
        "-show_streams",
        file_path,
    ]
    completed = subprocess.run(cmd, check=True, capture_output=True, text=True)
    payload = json.loads(completed.stdout)
    return parse_probe_payload(payload)
