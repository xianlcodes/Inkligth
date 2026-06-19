import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey
from app.db.database import AlibabaBase


class AIEngine(AlibabaBase):
    __tablename__ = "ai_engines"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    provider = Column(String, nullable=False)
    api_base = Column(String, nullable=False)
    api_key = Column(String, nullable=False)
    default_model = Column(String, nullable=False)
    fallback_models = Column(String, nullable=True)
    is_default = Column(Boolean, default=False, nullable=False)
    proxy_enabled = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
