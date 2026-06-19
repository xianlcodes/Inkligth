import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, JSON, Text
from app.db.database import TencentBase


class Presentation(TencentBase):
    __tablename__ = "presentations"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    # user_id 无 FK 约束（跨库引用 users.id）
    user_id = Column(String, nullable=False, index=True)
    literature_id = Column(String, ForeignKey("literatures.id", ondelete="SET NULL"), nullable=True, index=True)
    literature_title = Column(String(500), nullable=True)
    slides = Column(JSON, nullable=False, default=list)
    slide_count = Column(String, nullable=True)
    ppt_file_path = Column(String(1024), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
