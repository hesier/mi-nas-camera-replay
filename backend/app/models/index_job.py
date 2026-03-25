from sqlalchemy import Column, Integer, String, Text

from app.core.db import Base


class IndexJob(Base):
    __tablename__ = "index_jobs"

    id = Column(Integer, primary_key=True)
    job_day = Column(String, nullable=False)
    status = Column(String, nullable=False)
    scanned_count = Column(Integer, nullable=False, default=0)
    success_count = Column(Integer, nullable=False, default=0)
    warning_count = Column(Integer, nullable=False, default=0)
    failed_count = Column(Integer, nullable=False, default=0)
    started_at = Column(Text, nullable=False)
    finished_at = Column(Text, nullable=True)
