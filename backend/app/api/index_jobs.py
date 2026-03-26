from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session, sessionmaker

from app.core.auth import require_authenticated
from app.core.db import get_db
from app.schemas.locate import RebuildResponse
from app.tasks.index_videos import enqueue_index_job

router = APIRouter(dependencies=[Depends(require_authenticated)])


@router.post("/api/index/rebuild", response_model=RebuildResponse)
def rebuild_index(
    day: Optional[date] = None,
    session: Session = Depends(get_db),
) -> RebuildResponse:
    target_day = day.isoformat() if day is not None else None
    session_factory = sessionmaker(
        bind=session.get_bind(),
        autoflush=False,
        autocommit=False,
        future=True,
    )
    job = enqueue_index_job(
        target_day=target_day,
        session_factory=session_factory,
    )
    return RebuildResponse(
        accepted=True,
        jobId=job.id,
        scope="day" if target_day is not None else "all",
        day=target_day,
    )
