from sqlalchemy import Column, Float, Integer, String, Text

from app.core.db import Base


class VideoFile(Base):
    __tablename__ = "video_files"

    id = Column(Integer, primary_key=True)
    file_path = Column(Text, unique=True, nullable=False)
    file_name = Column(String, nullable=False)
    file_size = Column(Integer, nullable=False)
    file_mtime = Column(Text, nullable=False)
    name_start_at = Column(Text, nullable=True)
    name_end_at = Column(Text, nullable=True)
    probe_duration_sec = Column(Float, nullable=True)
    actual_start_at = Column(Text, nullable=True)
    actual_end_at = Column(Text, nullable=True)
    time_source = Column(String, nullable=False)
    status = Column(String, nullable=False)
    issue_flags = Column(Text, nullable=True)
    created_at = Column(Text, nullable=False)
    updated_at = Column(Text, nullable=False)
