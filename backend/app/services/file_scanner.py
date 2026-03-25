from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ScannedVideoFile:
    path: Path
    name: str
    file_size: int
    file_mtime: int


def scan_video_files(root: str | Path) -> list[ScannedVideoFile]:
    root_path = Path(root)
    if not root_path.exists():
        return []

    results: list[ScannedVideoFile] = []
    for file_path in sorted(path for path in root_path.rglob("*") if path.is_file()):
        if file_path.suffix.lower() != ".mp4":
            continue
        stat = file_path.stat()
        results.append(
            ScannedVideoFile(
                path=file_path,
                name=file_path.name,
                file_size=stat.st_size,
                file_mtime=int(stat.st_mtime),
            )
        )
    return results


def should_reprobe(existing, incoming) -> bool:
    return (
        existing.file_size != incoming.file_size
        or existing.file_mtime != incoming.file_mtime
    )
