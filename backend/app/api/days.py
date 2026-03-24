from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.models import DaySummary
from app.schemas.day import DayItem

router = APIRouter()


@router.get("/api/days", response_model=list[DayItem])
def list_days(session: Session = Depends(get_db)) -> list[DayItem]:
    rows = session.query(DaySummary).order_by(DaySummary.day.desc()).all()
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
