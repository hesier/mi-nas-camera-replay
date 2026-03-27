from pydantic import BaseModel


class CameraItem(BaseModel):
    cameraNo: int
    label: str
