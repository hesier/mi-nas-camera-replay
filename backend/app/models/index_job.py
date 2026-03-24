from sqlalchemy import Column, Integer, String, Text

from app.core.db import Base


class IndexJob(Base):
    __tablename__ = "index_jobs"

    id = Column(Integer, primary_key=True)
    status = Column(String, nullable=False)
    started_at = Column(Text, nullable=False)
    finished_at = Column(Text, nullable=True)
