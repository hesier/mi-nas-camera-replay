from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.auth import require_authenticated
from app.core.config import Settings, get_settings
from app.core.db import get_db
from app.schemas.locate import LocateResponse
from app.services.locate_service import locate_at

router = APIRouter(dependencies=[Depends(require_authenticated)])


@router.get("/api/locate", response_model=LocateResponse)
def locate(
    camera: int,
    at: datetime,
    session: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> LocateResponse:
    configured_cameras = {item.camera_no for item in settings.camera_roots}
    if camera not in configured_cameras:
        raise HTTPException(status_code=404, detail="camera not found")

    return LocateResponse(
        **locate_at(
            session,
            at,
            camera_no=camera,
            timezone_name=settings.timezone,
        )
    )
