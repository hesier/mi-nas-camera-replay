from __future__ import annotations

import os
import re
from dataclasses import dataclass
from datetime import time
from functools import lru_cache
from pathlib import Path

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


@dataclass(frozen=True)
class CameraRoot:
    camera_no: int
    video_root: str


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        # 允许从 .env 中保留 VIDEO_ROOT_数字 这类动态配置键，供 camera_roots 解析使用
        extra="allow",
    )

    timezone: str = "Asia/Shanghai"
    sqlite_url: str = "sqlite:///./replay.db"
    video_root: str = "./videos"
    app_password: str = ""
    index_on_startup: bool = False
    index_scheduler_enabled: bool = False
    index_scheduler_time: time = "03:00"
    cors_origins: list[str] = [
        "http://127.0.0.1:4173",
        "http://localhost:4173",
        "http://127.0.0.1:5173",
        "http://localhost:5173",
    ]

    @field_validator("index_scheduler_time", mode="before")
    @classmethod
    def normalize_index_scheduler_time(cls, value: object) -> object:
        if not isinstance(value, str):
            return value

        parts = value.strip().split(":")
        if len(parts) != 2:
            return value

        hour, minute = parts
        if not hour.isdigit() or not minute.isdigit():
            return value

        return f"{int(hour):02d}:{int(minute):02d}"

    @model_validator(mode="after")
    def validate_required_light_config(self) -> "Settings":
        if not self.app_password or not self.app_password.strip():
            raise ValueError("必须配置非空的 APP_PASSWORD")

        # 触发 VIDEO_ROOT_数字 的校验（重复/重叠/至少一个）
        _ = self.camera_roots
        return self

    @property
    def camera_roots(self) -> list[CameraRoot]:
        video_roots_by_no: dict[int, str] = {}

        # 1) 先取 settings 已加载的 extra（例如来自 .env 的 VIDEO_ROOT_数字）
        extra = self.model_extra or {}
        for key, value in extra.items():
            camera_no = _parse_video_root_camera_no(key)
            if camera_no is None:
                continue
            if isinstance(value, str) and value.strip():
                video_roots_by_no[camera_no] = value.strip()

        # 2) 再用真实环境变量覆盖（通常优先级高于 .env）
        for key, value in os.environ.items():
            camera_no = _parse_video_root_camera_no(key)
            if camera_no is None:
                continue
            if isinstance(value, str) and value.strip():
                video_roots_by_no[camera_no] = value.strip()

        if not video_roots_by_no:
            raise ValueError("至少需要配置一个 VIDEO_ROOT_数字（例如 VIDEO_ROOT_1）")

        camera_roots = [
            CameraRoot(camera_no=camera_no, video_root=video_root)
            for camera_no, video_root in sorted(video_roots_by_no.items())
        ]

        _validate_video_roots_no_overlap(camera_roots)
        return camera_roots


@lru_cache
def get_settings() -> Settings:
    return Settings()


_VIDEO_ROOT_KEY_RE = re.compile(r"^VIDEO_ROOT_(\d+)$", re.IGNORECASE)


def _parse_video_root_camera_no(key: str) -> int | None:
    match = _VIDEO_ROOT_KEY_RE.match(key)
    if not match:
        return None
    camera_no = int(match.group(1))
    if camera_no <= 0:
        return None
    return camera_no


def _normalize_video_root_path(path_value: str) -> Path:
    # strict=False：目录不需要预先存在，也能做重复/重叠校验
    return Path(path_value).expanduser().resolve(strict=False)


def _validate_video_roots_no_overlap(camera_roots: list[CameraRoot]) -> None:
    normalized: list[tuple[int, str, Path]] = [
        (root.camera_no, root.video_root, _normalize_video_root_path(root.video_root))
        for root in camera_roots
    ]

    # 1) 重复目录
    seen: dict[Path, int] = {}
    for camera_no, raw_value, norm_path in normalized:
        other = seen.get(norm_path)
        if other is not None:
            raise ValueError(
                f"视频目录不允许重复：VIDEO_ROOT_{other} 与 VIDEO_ROOT_{camera_no} 指向同一目录（{raw_value}）"
            )
        seen[norm_path] = camera_no

    # 2) 父子重叠
    for i in range(len(normalized)):
        a_no, a_raw, a_path = normalized[i]
        for j in range(i + 1, len(normalized)):
            b_no, b_raw, b_path = normalized[j]

            if a_path in b_path.parents or b_path in a_path.parents:
                raise ValueError(
                    "视频目录不允许父子重叠："
                    f"VIDEO_ROOT_{a_no}={a_raw} 与 VIDEO_ROOT_{b_no}={b_raw}"
                )
