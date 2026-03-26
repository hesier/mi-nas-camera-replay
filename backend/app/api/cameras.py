from fastapi import APIRouter, Depends

from app.core.config import Settings, get_settings
from app.schemas.camera import CameraItem

router = APIRouter()


@router.get("/api/cameras", response_model=list[CameraItem])
def list_cameras(settings: Settings = Depends(get_settings)) -> list[CameraItem]:
    return [
        CameraItem(cameraNo=item.camera_no, label=f"通道 {item.camera_no}")
        for item in settings.camera_roots
    ]
