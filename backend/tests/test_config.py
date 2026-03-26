from app.core.config import Settings


def test_settings_auto_loads_dotenv_in_current_directory(monkeypatch, tmp_path):
    dotenv_path = tmp_path / ".env"
    dotenv_path.write_text(
        "\n".join(
            [
                "VIDEO_ROOT=/tmp/nas-videos",
                "INDEX_ON_STARTUP=true",
                "INDEX_SCHEDULER_ENABLED=true",
                "INDEX_SCHEDULER_TIME=3:00",
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)

    settings = Settings()

    assert settings.video_root == "/tmp/nas-videos"
    assert settings.index_on_startup is True
    assert settings.index_scheduler_enabled is True
    assert settings.index_scheduler_time.isoformat() == "03:00:00"
