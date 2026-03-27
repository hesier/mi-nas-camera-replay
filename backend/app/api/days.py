from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.auth import require_authenticated
from app.core.config import Settings, get_settings
from app.core.db import get_db
from app.models import DaySummary
from app.schemas.day import DayItem

router = APIRouter(dependencies=[Depends(require_authenticated)])


@router.get("/api/days", response_model=list[DayItem])
def list_days(
    camera: int,
    session: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> list[DayItem]:
    configured_cameras = {item.camera_no for item in settings.camera_roots}
    if camera not in configured_cameras:
        raise HTTPException(status_code=404, detail="camera not found")

    rows = (
        session.query(DaySummary)
        .filter(DaySummary.camera_no == camera)
        .order_by(DaySummary.day.desc())
        .all()
    )
    return [
        DayItem(
            day=row.day,
            segmentCount=row.total_segment_count,
            recordedSeconds=float(row.total_recorded_sec),
            gapSeconds=float(row.total_gap_sec),
            hasWarning=bool(row.has_warning),
            firstSegmentAt=row.first_segment_at,
            lastSegmentAt=row.last_segment_at,
        )
        for row in rows
    ]
