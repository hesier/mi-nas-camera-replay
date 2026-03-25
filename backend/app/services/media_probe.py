from __future__ import annotations

import json
import math
import subprocess
from dataclasses import dataclass
from typing import Any, Mapping

FFPROBE_TIMEOUT_SEC = 15.0


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
    if (not math.isfinite(duration_sec)) or duration_sec < 0:
        raise ValueError("invalid ffprobe duration")

    raw_start_time = format_payload.get("start_time", 0.0)
    try:
        start_time_sec = float(raw_start_time)
    except (TypeError, ValueError) as exc:
        raise ValueError("invalid ffprobe start_time") from exc
    if not math.isfinite(start_time_sec):
        raise ValueError("invalid ffprobe start_time")

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
    try:
        completed = subprocess.run(
            cmd,
            check=True,
            capture_output=True,
            text=True,
            timeout=FFPROBE_TIMEOUT_SEC,
        )
    except (subprocess.SubprocessError, OSError) as exc:
        raise ValueError("ffprobe execution failed") from exc
    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise ValueError("invalid ffprobe json output") from exc
    return parse_probe_payload(payload)
