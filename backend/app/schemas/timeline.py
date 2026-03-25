from __future__ import annotations

from pydantic import BaseModel


class TimelineSummary(BaseModel):
    segmentCount: int
    recordedSeconds: float
    gapSeconds: float
    warningCount: int


class TimelineSegmentItem(BaseModel):
    id: int
    fileId: int
    startAt: str
    endAt: str
    durationSec: float
    playbackUrl: str
    fileOffsetSec: float
    status: str
    issueFlags: list[str]


class TimelineGapItem(BaseModel):
    startAt: str
    endAt: str
    durationSec: float


class TimelineResponse(BaseModel):
    day: str
    timezone: str
    summary: TimelineSummary
    segments: list[TimelineSegmentItem]
    gaps: list[TimelineGapItem]
