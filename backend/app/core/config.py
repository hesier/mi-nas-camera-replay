from __future__ import annotations

import os
import re
from dataclasses import dataclass
from datetime import time
from functools import cached_property, lru_cache
from pathlib import Path

from pydantic import field_validator, model_validator
from pydantic_settings import (
    BaseSettings,
    EnvSettingsSource,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
)


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

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        # 默认 EnvSettingsSource 只读取已声明的字段，不会把 VIDEO_ROOT_数字 作为 extra 读进来。
        # 这里补一个轻量 Source，将 VIDEO_ROOT_数字 合并进 Settings 初始化结果，之后 camera_roots
        # 只从实例快照读取，避免同一 Settings 实例随着 os.environ 变化而漂移。
        return (
            init_settings,
            _ExtraVideoRootEnvSettingsSource(settings_cls),
            dotenv_settings,
            file_secret_settings,
        )

    @model_validator(mode="after")
    def validate_required_light_config(self) -> "Settings":
        if not self.app_password or not self.app_password.strip():
            raise ValueError("必须配置非空的 APP_PASSWORD")

        # 触发 VIDEO_ROOT_数字 的校验（重复/重叠/至少一个）
        roots = self.camera_roots

        # 兼容旧 VIDEO_ROOT：如果显式设置了旧字段，则必须与 VIDEO_ROOT_1 完全一致，
        # 否则会出现双真相（video_root 与 camera_roots[0].video_root 指向不同目录）。
        if "video_root" in self.model_fields_set:
            if self.video_root != roots[0].video_root:
                raise ValueError(
                    "旧配置 VIDEO_ROOT 必须与 VIDEO_ROOT_1 完全一致，"
                    f"当前 VIDEO_ROOT={self.video_root} VIDEO_ROOT_1={roots[0].video_root}"
                )

        # 旧消费方仍在读取 settings.video_root，这里将其与新配置对齐：
        # 当未显式设置 video_root 时，默认使用 camera_roots[0]。
        if "video_root" not in self.model_fields_set and self.video_root == "./videos":
            self.video_root = roots[0].video_root
        return self

    @cached_property
    def camera_roots(self) -> list[CameraRoot]:
        video_roots_by_no: dict[int, str] = {}

        # 只读取 Settings 初始化后的快照（extra），不要每次访问都读取 os.environ
        extra = self.model_extra or {}
        for key, value in extra.items():
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
    match = _VIDEO_ROOT_KEY_RE.match(key.upper())
    if not match:
        return None
    camera_no = int(match.group(1))
    if camera_no <= 0:
        return None
    return camera_no


class _ExtraVideoRootEnvSettingsSource(EnvSettingsSource):
    def __call__(self) -> dict[str, object]:
        data: dict[str, object] = super().__call__()

        # 仅补充 VIDEO_ROOT_数字 这一类 extra 键
        for env_name, env_value in os.environ.items():
            if not env_value:
                continue
            if _parse_video_root_camera_no(env_name) is None:
                continue
            data[env_name.upper()] = env_value

        return data


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
