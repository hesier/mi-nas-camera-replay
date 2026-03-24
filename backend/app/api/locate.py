from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.db import get_db
from app.schemas.locate import LocateResponse
from app.services.locate_service import locate_at

router = APIRouter()


@router.get("/api/locate", response_model=LocateResponse)
def locate(
    at: datetime,
    session: Session = Depends(get_db),
) -> LocateResponse:
    return LocateResponse(
        **locate_at(
            session,
            at,
            timezone_name=get_settings().timezone,
        )
    )
