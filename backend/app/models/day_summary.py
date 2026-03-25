from sqlalchemy import Boolean, Column, Float, Integer, String, Text

from app.core.db import Base


class DaySummary(Base):
    __tablename__ = "day_summaries"

    day = Column(String, primary_key=True)
    first_segment_at = Column(Text, nullable=True)
    last_segment_at = Column(Text, nullable=True)
    total_segment_count = Column(Integer, nullable=False, default=0)
    total_recorded_sec = Column(Float, nullable=False, default=0.0)
    total_gap_sec = Column(Float, nullable=False, default=0.0)
    has_warning = Column(Boolean, nullable=False, default=False)
    updated_at = Column(Text, nullable=False)
