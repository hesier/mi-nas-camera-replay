from sqlalchemy import Boolean, Column, Float, Integer, String, Text

from app.core.db import Base


class DaySummary(Base):
    __tablename__ = "day_summaries"

    id = Column(Integer, primary_key=True)
    day = Column(String, unique=True, nullable=False)
    first_segment_at = Column(Text, nullable=True)
    last_segment_at = Column(Text, nullable=True)
    total_segment_count = Column(Integer, nullable=False, default=0)
    total_recorded_sec = Column(Float, nullable=False, default=0.0)
    total_gap_sec = Column(Float, nullable=False, default=0.0)
    has_warning = Column(Boolean, nullable=False, default=False)
    updated_at = Column(Text, nullable=False)
