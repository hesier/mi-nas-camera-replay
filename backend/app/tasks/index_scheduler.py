from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import datetime, time, timedelta
from threading import Event, Thread, current_thread
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.db import SessionLocal
from app.tasks.index_videos import run_index_job

logger = logging.getLogger(__name__)


def _normalize_datetime(value: datetime, timezone_name: str) -> datetime:
    timezone = ZoneInfo(timezone_name)
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone)
    return value.astimezone(timezone)


def get_next_run_at(
    *,
    now: datetime,
    schedule_time: time,
    timezone_name: str,
) -> datetime:
    localized_now = _normalize_datetime(now, timezone_name)
    next_run = localized_now.replace(
        hour=schedule_time.hour,
        minute=schedule_time.minute,
        second=schedule_time.second,
        microsecond=0,
    )
    if next_run <= localized_now:
        return next_run + timedelta(days=1)
    return next_run


class DailyIndexScheduler:
    def __init__(
        self,
        *,
        schedule_time: time,
        timezone_name: str,
        runner: Callable[[], None],
    ) -> None:
        self.schedule_time = schedule_time
        self.timezone_name = timezone_name
        self.runner = runner
        self._stop_event = Event()
        self._thread: Thread | None = None

    def start(self) -> "DailyIndexScheduler":
        if self._thread is not None and self._thread.is_alive():
            return self

        self._stop_event.clear()
        self._thread = Thread(
            target=self._run_loop,
            name="daily-index-scheduler",
            daemon=True,
        )
        self._thread.start()
        return self

    def stop(self, *, timeout: float = 5.0) -> None:
        self._stop_event.set()
        if self._thread is None or self._thread is current_thread():
            return
        self._thread.join(timeout=timeout)

    def _run_loop(self) -> None:
        while not self._stop_event.is_set():
            now = datetime.now(tz=ZoneInfo(self.timezone_name))
            next_run = get_next_run_at(
                now=now,
                schedule_time=self.schedule_time,
                timezone_name=self.timezone_name,
            )
            wait_seconds = max((next_run - now).total_seconds(), 0.0)
            if self._stop_event.wait(wait_seconds):
                return

            try:
                self.runner()
            except Exception:
                logger.exception("内建索引调度器执行失败")


def run_scheduled_index_job(
    *,
    settings: Settings | None = None,
    session_factory: Callable[[], Session] = SessionLocal,
) -> None:
    current_settings = settings or get_settings()
    session = session_factory()
    try:
        run_index_job(
            session,
            camera_roots=current_settings.camera_roots,
            target_day=None,
        )
    finally:
        session.close()


def start_index_scheduler(
    *,
    settings: Settings | None = None,
    session_factory: Callable[[], Session] = SessionLocal,
) -> DailyIndexScheduler | None:
    current_settings = settings or get_settings()
    if not current_settings.index_scheduler_enabled:
        return None

    scheduler = DailyIndexScheduler(
        schedule_time=current_settings.index_scheduler_time,
        timezone_name=current_settings.timezone,
        runner=lambda: run_scheduled_index_job(
            settings=current_settings,
            session_factory=session_factory,
        ),
    )
    return scheduler.start()


def stop_index_scheduler(scheduler: DailyIndexScheduler | None) -> None:
    if scheduler is None:
        return
    scheduler.stop()
