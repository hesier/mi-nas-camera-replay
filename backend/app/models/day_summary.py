from sqlalchemy import Boolean, Column, Float, Integer, String, Text, UniqueConstraint, text

from app.core.db import Base


class DaySummary(Base):
    __tablename__ = "day_summaries"

    __table_args__ = (
        # 未来按通道查询时以 camera_no + day 作为自然键；id 仅做稳定主键/外键用途
        UniqueConstraint("camera_no", "day", name="uq_day_summaries_camera_day"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    # 目前系统仍以单通道为主，先给出默认值 1，后续 Task 3 会按来源写入真实 camera_no
    camera_no = Column(Integer, nullable=False, server_default=text("1"), default=1)
    day = Column(String, nullable=False)
    first_segment_at = Column(Text, nullable=True)
    last_segment_at = Column(Text, nullable=True)
    total_segment_count = Column(Integer, nullable=False, default=0)
    total_recorded_sec = Column(Float, nullable=False, default=0.0)
    total_gap_sec = Column(Float, nullable=False, default=0.0)
    has_warning = Column(Boolean, nullable=False, default=False)
    updated_at = Column(Text, nullable=False)
