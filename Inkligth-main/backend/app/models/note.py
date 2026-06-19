import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Text, ForeignKey
from sqlalchemy.dialects.postgresql import JSON
from app.db.database import TencentBase


class Note(TencentBase):
    __tablename__ = "notes"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    # user_id 无 FK 约束（跨库引用 users.id）
    user_id = Column(String, nullable=False, index=True)
    literature_id = Column(String, ForeignKey("literatures.id", ondelete="CASCADE"), nullable=False, index=True)
    page_number = Column(String, nullable=False)
    rect_coords = Column(JSON, nullable=False)
    quoted_text = Column(Text, nullable=True)
    content = Column(Text, nullable=True)
    note_type = Column(String, default="general")
    created_at = Column(DateTime, default=datetime.utcnow)
