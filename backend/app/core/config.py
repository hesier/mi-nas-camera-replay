from datetime import time
from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )

    timezone: str = "Asia/Shanghai"
    sqlite_url: str = "sqlite:///./replay.db"
    video_root: str = "./videos"
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


@lru_cache
def get_settings() -> Settings:
    return Settings()
