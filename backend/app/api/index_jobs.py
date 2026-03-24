from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.schemas.locate import RebuildResponse
from app.tasks.index_videos import run_index_job

router = APIRouter()


@router.post("/api/index/rebuild", response_model=RebuildResponse)
def rebuild_index(
    day: Optional[date] = None,
    session: Session = Depends(get_db),
) -> RebuildResponse:
    target_day = day.isoformat() if day is not None else None
    job = run_index_job(session=session, target_day=target_day)
    return RebuildResponse(
        accepted=True,
        jobId=job.id,
        scope="day" if target_day is not None else "all",
        day=target_day,
    )
