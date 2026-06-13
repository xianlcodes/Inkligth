import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Text, ForeignKey
from sqlalchemy.dialects.postgresql import JSON
from app.db.database import AlibabaBase


class AIAnalysis(AlibabaBase):
    __tablename__ = "ai_analyses"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    # literature_id 无 FK 约束（跨库引用 literatures.id）
    literature_id = Column(String, nullable=False, unique=True, index=True)
    summary = Column(JSON, nullable=True)
    innovations = Column(JSON, nullable=True)
    methods = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
