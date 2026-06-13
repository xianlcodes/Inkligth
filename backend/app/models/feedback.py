import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Text, Boolean
from app.db.database import AlibabaBase


class Feedback(AlibabaBase):
    __tablename__ = "feedback"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, nullable=False, index=True)
    user_email = Column(String, nullable=True)
    user_name = Column(String, nullable=True)
    content = Column(Text, nullable=False)
    page_url = Column(String, nullable=True)
    browser_info = Column(String, nullable=True)
    is_resolved = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
