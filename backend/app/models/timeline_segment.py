from sqlalchemy import Column, Integer, String, Text

from app.core.db import Base


class TimelineSegment(Base):
    __tablename__ = "timeline_segments"

    id = Column(Integer, primary_key=True)
    day = Column(String, nullable=False)
    start_at = Column(Text, nullable=False)
    end_at = Column(Text, nullable=False)
