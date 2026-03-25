from typing import Optional

from pydantic import BaseModel


class LocateSegmentItem(BaseModel):
    id: int
    fileId: int
    startAt: str
    endAt: str
    durationSec: float
    playbackUrl: str
    fileOffsetSec: float
    status: str
    issueFlags: list[str]


class LocateGapItem(BaseModel):
    startAt: str
    endAt: str


class LocateResponse(BaseModel):
    found: bool
    segment: Optional[LocateSegmentItem]
    seekOffsetSec: Optional[float]
    gap: Optional[LocateGapItem]
    nextSegment: Optional[LocateSegmentItem]


class RebuildResponse(BaseModel):
    accepted: bool
    jobId: int
    scope: str
    day: Optional[str]
