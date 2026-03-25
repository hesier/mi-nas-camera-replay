from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    timezone: str = "Asia/Shanghai"
    sqlite_url: str = "sqlite:///./replay.db"
    video_root: str = "./videos"
    cors_origins: list[str] = [
        "http://127.0.0.1:4173",
        "http://localhost:4173",
        "http://127.0.0.1:5173",
        "http://localhost:5173",
    ]


@lru_cache
def get_settings() -> Settings:
    return Settings()
