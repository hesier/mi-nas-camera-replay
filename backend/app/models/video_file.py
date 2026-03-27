from sqlalchemy import Column, Float, Integer, String, Text, text

from app.core.db import Base


class VideoFile(Base):
    __tablename__ = "video_files"

    id = Column(Integer, primary_key=True)
    # 目前系统仍以单通道为主，先给出默认值 1，后续 Task 3 会按文件/配置写入真实 camera_no
    camera_no = Column(Integer, nullable=False, server_default=text("1"), default=1)
    file_path = Column(Text, unique=True, nullable=False)
    file_name = Column(String, nullable=False)
    file_size = Column(Integer, nullable=False)
    file_mtime = Column(Integer, nullable=False)
    name_start_at = Column(Text, nullable=True)
    name_end_at = Column(Text, nullable=True)
    probe_duration_sec = Column(Float, nullable=True)
    probe_video_codec = Column(String, nullable=True)
    probe_audio_codec = Column(String, nullable=True)
    probe_width = Column(Integer, nullable=True)
    probe_height = Column(Integer, nullable=True)
    probe_start_time_sec = Column(Float, nullable=True)
    actual_start_at = Column(Text, nullable=True)
    actual_end_at = Column(Text, nullable=True)
    time_source = Column(String, nullable=False)
    status = Column(String, nullable=False)
    issue_flags = Column(Text, nullable=True)
    created_at = Column(Text, nullable=False)
    updated_at = Column(Text, nullable=False)
