from sqlalchemy import Column, Float, ForeignKey, Integer, String, Text, text

from app.core.db import Base


class TimelineSegment(Base):
    __tablename__ = "timeline_segments"

    id = Column(Integer, primary_key=True)
    file_id = Column(Integer, ForeignKey("video_files.id"), nullable=False)
    # 目前系统仍以单通道为主，先给出默认值 1，后续 Task 3 会按来源写入真实 camera_no
    camera_no = Column(Integer, nullable=False, server_default=text("1"), default=1)
    day = Column(String, nullable=False)
    segment_start_at = Column(Text, nullable=False)
    segment_end_at = Column(Text, nullable=False)
    duration_sec = Column(Float, nullable=False)
    playback_url = Column(Text, nullable=False)
    file_offset_sec = Column(Float, nullable=False, server_default=text("0"))
    prev_gap_sec = Column(Float, nullable=True)
    next_gap_sec = Column(Float, nullable=True)
    status = Column(String, nullable=False)
