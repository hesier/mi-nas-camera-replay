from typing import Optional

from pydantic import BaseModel


class DayItem(BaseModel):
    day: str
    segmentCount: int
    recordedSeconds: float
    gapSeconds: float
    hasWarning: bool
    firstSegmentAt: Optional[str]
    lastSegmentAt: Optional[str]
