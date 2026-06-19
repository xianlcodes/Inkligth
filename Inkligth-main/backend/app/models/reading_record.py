import uuid
from datetime import datetime, date
from sqlalchemy import Column, String, Integer, Float, Date, DateTime, ForeignKey
from app.db.database import TencentBase


class ReadingRecord(TencentBase):
    __tablename__ = "reading_records"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    # user_id 无 FK 约束（跨库引用 users.id）
    user_id = Column(String, nullable=False, index=True)
    literature_id = Column(String, ForeignKey("literatures.id", ondelete="CASCADE"), nullable=False, index=True)
    record_date = Column(Date, nullable=False, index=True)
    pages_read = Column(Integer, default=0)
    reading_time_seconds = Column(Integer, default=0)
    last_page = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
