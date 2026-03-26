from __future__ import annotations

from datetime import datetime, time
from zoneinfo import ZoneInfo

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app
from app.tasks.index_scheduler import (
    get_next_run_at,
    run_scheduled_index_job,
    start_index_scheduler,
)


def test_settings_supports_string_scheduler_time_formats():
    assert Settings().index_scheduler_time == time(hour=3, minute=0)
    assert Settings(index_scheduler_time="3:00").index_scheduler_time == time(
        hour=3,
        minute=0,
    )


def test_get_next_run_at_returns_same_day_when_schedule_is_ahead():
    next_run = get_next_run_at(
        now=datetime(2026, 3, 26, 1, 30, tzinfo=ZoneInfo("Asia/Shanghai")),
        schedule_time=time(hour=3, minute=0),
        timezone_name="Asia/Shanghai",
    )

    assert next_run.isoformat() == "2026-03-26T03:00:00+08:00"


def test_get_next_run_at_rolls_to_next_day_when_schedule_has_passed():
    next_run = get_next_run_at(
        now=datetime(2026, 3, 26, 3, 0, tzinfo=ZoneInfo("Asia/Shanghai")),
        schedule_time=time(hour=3, minute=0),
        timezone_name="Asia/Shanghai",
    )

    assert next_run.isoformat() == "2026-03-27T03:00:00+08:00"


def test_run_scheduled_index_job_uses_configured_root_and_closes_session(
    monkeypatch,
    tmp_path,
):
    class FakeSession:
        def __init__(self) -> None:
            self.closed = False

        def close(self) -> None:
            self.closed = True

    session = FakeSession()
    called: dict[str, object] = {}

    monkeypatch.setattr(
        "app.tasks.index_scheduler.run_index_job",
        lambda db_session, *, root, target_day=None: called.update(
            {
                "session": db_session,
                "root": root,
                "target_day": target_day,
            }
        ),
    )

    run_scheduled_index_job(
        settings=Settings(video_root=str(tmp_path)),
        session_factory=lambda: session,
    )

    assert called == {
        "session": session,
        "root": str(tmp_path),
        "target_day": None,
    }
    assert session.closed is True


def test_start_index_scheduler_returns_none_when_disabled(monkeypatch):
    monkeypatch.setattr(
        "app.tasks.index_scheduler.DailyIndexScheduler",
        lambda **_: (_ for _ in ()).throw(AssertionError("不应创建调度器")),
    )

    result = start_index_scheduler(settings=Settings(index_scheduler_enabled=False))

    assert result is None


def test_start_index_scheduler_builds_and_starts_scheduler(monkeypatch, tmp_path):
    created: dict[str, object] = {}

    class FakeScheduler:
        def __init__(self, *, schedule_time, timezone_name, runner) -> None:
            created["schedule_time"] = schedule_time
            created["timezone_name"] = timezone_name
            created["runner"] = runner
            created["started"] = False

        def start(self) -> "FakeScheduler":
            created["started"] = True
            return self

    monkeypatch.setattr("app.tasks.index_scheduler.DailyIndexScheduler", FakeScheduler)

    scheduler = start_index_scheduler(
        settings=Settings(
            timezone="Asia/Shanghai",
            video_root=str(tmp_path),
            index_scheduler_enabled=True,
            index_scheduler_time="02:30",
        ),
        session_factory=lambda: object(),
    )

    assert scheduler is not None
    assert created["schedule_time"] == time(hour=2, minute=30)
    assert created["timezone_name"] == "Asia/Shanghai"
    assert callable(created["runner"])
    assert created["started"] is True


def test_app_lifespan_starts_and_stops_index_scheduler(monkeypatch):
    events: dict[str, object] = {}
    scheduler_handle = object()

    monkeypatch.setattr(
        "app.main.start_index_scheduler",
        lambda: events.setdefault("started", scheduler_handle),
    )
    monkeypatch.setattr(
        "app.main.stop_index_scheduler",
        lambda handle: events.setdefault("stopped", handle),
    )

    app = create_app()

    with TestClient(app):
        assert app.state.index_scheduler is scheduler_handle

    assert events["started"] is scheduler_handle
    assert events["stopped"] is scheduler_handle
