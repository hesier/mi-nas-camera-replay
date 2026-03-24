from sqlalchemy import Column, Integer, String, Text

from app.core.db import Base


class DaySummary(Base):
    __tablename__ = "day_summaries"

    id = Column(Integer, primary_key=True)
    day = Column(String, unique=True, nullable=False)
    preview_image_path = Column(Text, nullable=False)
