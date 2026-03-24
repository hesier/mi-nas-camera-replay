from sqlalchemy import Column, Integer, String, Text

from app.core.db import Base


class VideoFile(Base):
    __tablename__ = "video_files"

    id = Column(Integer, primary_key=True)
    file_path = Column(Text, unique=True, nullable=False)
    status = Column(String, nullable=False)
