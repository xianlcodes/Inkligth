import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Text
from sqlalchemy.dialects.postgresql import JSON
from app.db.database import TencentBase


class AIAnalysis(TencentBase):
    __tablename__ = "ai_analyses"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    # user_id 无 FK 约束（跨库引用 users.id）
    user_id = Column(String, nullable=False, index=True)
    # literature_id 无 FK 约束 — 同库引用 literatures.id，由业务逻辑保证一致性
    literature_id = Column(String, nullable=False, unique=True, index=True)
    summary = Column(JSON, nullable=True)
    innovations = Column(JSON, nullable=True)
    methods = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
