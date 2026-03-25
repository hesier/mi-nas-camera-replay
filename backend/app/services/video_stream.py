from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterator


CHUNK_SIZE = 64 * 1024


@dataclass(frozen=True)
class ByteRange:
    start: int
    end: int

    @property
    def content_length(self) -> int:
        return self.end - self.start + 1


def parse_range_header(header_value: str, file_size: int) -> ByteRange:
    if not header_value.startswith("bytes="):
        raise ValueError("invalid range")

    spec = header_value.removeprefix("bytes=")
    if "," in spec:
        raise ValueError("invalid range")

    start_text, sep, end_text = spec.partition("-")
    if sep != "-":
        raise ValueError("invalid range")

    if start_text == "" and end_text == "":
        raise ValueError("invalid range")

    if start_text == "":
        suffix_length = int(end_text)
        if suffix_length <= 0:
            raise ValueError("invalid range")
        if file_size <= 0:
            raise ValueError("invalid range")
        start = max(file_size - suffix_length, 0)
        return ByteRange(start=start, end=file_size - 1)

    start = int(start_text)
    if start < 0 or start >= file_size:
        raise ValueError("invalid range")

    if end_text == "":
        end = file_size - 1
    else:
        end = min(int(end_text), file_size - 1)

    if end < start:
        raise ValueError("invalid range")

    return ByteRange(start=start, end=end)


def iter_file_range(
    file_path: str | Path,
    byte_range: ByteRange,
    *,
    chunk_size: int = CHUNK_SIZE,
) -> Iterator[bytes]:
    remaining = byte_range.content_length
    with Path(file_path).open("rb") as file_obj:
        file_obj.seek(byte_range.start)
        while remaining > 0:
            chunk = file_obj.read(min(chunk_size, remaining))
            if not chunk:
                break
            remaining -= len(chunk)
            yield chunk
