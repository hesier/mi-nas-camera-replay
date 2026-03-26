import pytest
from pydantic import ValidationError

from app.core.config import CameraRoot, Settings


def test_settings_auto_loads_dotenv_in_current_directory(monkeypatch, tmp_path):
    # 避免系统环境变量覆盖 .env 中的配置
    monkeypatch.delenv("VIDEO_ROOT_1", raising=False)
    monkeypatch.delenv("VIDEO_ROOT_2", raising=False)
    monkeypatch.delenv("APP_PASSWORD", raising=False)

    dotenv_path = tmp_path / ".env"
    dotenv_path.write_text(
        "\n".join(
            [
                "VIDEO_ROOT_1=/tmp/nas-videos/cam1",
                "VIDEO_ROOT_2=/tmp/nas-videos/cam2",
                "APP_PASSWORD=test-password",
                "INDEX_ON_STARTUP=true",
                "INDEX_SCHEDULER_ENABLED=true",
                "INDEX_SCHEDULER_TIME=3:00",
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)

    settings = Settings()

    assert settings.camera_roots == [
        CameraRoot(camera_no=1, video_root="/tmp/nas-videos/cam1"),
        CameraRoot(camera_no=2, video_root="/tmp/nas-videos/cam2"),
    ]
    assert settings.app_password == "test-password"
    assert settings.index_on_startup is True
    assert settings.index_scheduler_enabled is True
    assert settings.index_scheduler_time.isoformat() == "03:00:00"


def test_settings_load_multiple_video_roots_and_password(monkeypatch, tmp_path):
    monkeypatch.delenv("VIDEO_ROOT_1", raising=False)
    monkeypatch.delenv("VIDEO_ROOT_2", raising=False)
    monkeypatch.delenv("APP_PASSWORD", raising=False)

    dotenv_path = tmp_path / ".env"
    dotenv_path.write_text(
        "\n".join(
            [
                "VIDEO_ROOT_2=./videos/cam2",
                "VIDEO_ROOT_1=./videos/cam1",
                "APP_PASSWORD=change-me",
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)

    settings = Settings()

    assert settings.app_password == "change-me"
    assert settings.camera_roots == [
        CameraRoot(camera_no=1, video_root="./videos/cam1"),
        CameraRoot(camera_no=2, video_root="./videos/cam2"),
    ]


def test_settings_reject_overlapping_video_roots(monkeypatch, tmp_path):
    monkeypatch.delenv("VIDEO_ROOT_1", raising=False)
    monkeypatch.delenv("VIDEO_ROOT_2", raising=False)
    monkeypatch.delenv("APP_PASSWORD", raising=False)

    dotenv_path = tmp_path / ".env"
    dotenv_path.write_text(
        "\n".join(
            [
                "VIDEO_ROOT_1=./videos",
                "VIDEO_ROOT_2=./videos/cam2",
                "APP_PASSWORD=change-me",
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)

    with pytest.raises(ValidationError):
        Settings()


def test_settings_require_at_least_one_video_root(monkeypatch, tmp_path):
    monkeypatch.delenv("VIDEO_ROOT_1", raising=False)
    monkeypatch.delenv("VIDEO_ROOT_2", raising=False)
    monkeypatch.delenv("APP_PASSWORD", raising=False)

    dotenv_path = tmp_path / ".env"
    dotenv_path.write_text(
        "\n".join(
            [
                "APP_PASSWORD=change-me",
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)

    with pytest.raises(ValidationError):
        Settings()


def test_settings_require_app_password(monkeypatch, tmp_path):
    monkeypatch.delenv("VIDEO_ROOT_1", raising=False)
    monkeypatch.delenv("VIDEO_ROOT_2", raising=False)
    monkeypatch.delenv("APP_PASSWORD", raising=False)

    dotenv_path = tmp_path / ".env"
    dotenv_path.write_text(
        "\n".join(
            [
                "VIDEO_ROOT_1=./videos/cam1",
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)

    with pytest.raises(ValidationError):
        Settings()
