from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo


FILENAME_RE = re.compile(r"^\d+_(\d{14})_(\d{14})\.mp4$")
_SHANGHAI_ZONE = ZoneInfo("Asia/Shanghai")


@dataclass(frozen=True)
class ParsedFilename:
    name_start_at: datetime
    name_end_at: datetime


def _parse_timestamp(value: str) -> datetime:
    return datetime.strptime(value, "%Y%m%d%H%M%S").replace(tzinfo=_SHANGHAI_ZONE)


def parse_camera_filename(file_name: str) -> ParsedFilename:
    match = FILENAME_RE.match(file_name)
    if not match:
        raise ValueError("invalid camera filename")

    start_at = _parse_timestamp(match.group(1))
    end_at = _parse_timestamp(match.group(2))
    return ParsedFilename(name_start_at=start_at, name_end_at=end_at)
