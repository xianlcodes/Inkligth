import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Boolean, Text
from app.db.database import AlibabaBase


class Announcement(AlibabaBase):
    __tablename__ = "announcements"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    level = Column(String, default="info")
    scope = Column(String, default="authenticated")
    is_pinned = Column(Boolean, default=False)
    is_published = Column(Boolean, default=False)
    published_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
