from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    timezone: str = "Asia/Shanghai"
    sqlite_url: str = "sqlite:///./replay.db"
    video_root: str


@lru_cache
def get_settings() -> Settings:
    return Settings()
