from sqlalchemy import Column, Float, ForeignKey, Integer, String, Text, text

from app.core.db import Base


class TimelineSegment(Base):
    __tablename__ = "timeline_segments"

    id = Column(Integer, primary_key=True)
    file_id = Column(Integer, ForeignKey("video_files.id"), nullable=False)
    day = Column(String, nullable=False)
    segment_start_at = Column(Text, nullable=False)
    segment_end_at = Column(Text, nullable=False)
    duration_sec = Column(Float, nullable=False)
    playback_url = Column(Text, nullable=False)
    file_offset_sec = Column(Float, nullable=False, server_default=text("0"))
    prev_gap_sec = Column(Float, nullable=True)
    next_gap_sec = Column(Float, nullable=True)
    status = Column(String, nullable=False)
