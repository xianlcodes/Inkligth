import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Text, Integer, UniqueConstraint
from app.db.database import Base


class TranslationCache(Base):
    __tablename__ = "translation_cache"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    engine_id = Column(String(128), nullable=False, index=True)
    text_hash = Column(String(64), nullable=False)
    source_text = Column(Text, nullable=False)
    translated_text = Column(Text, nullable=False)
    hit_count = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("engine_id", "text_hash", name="uq_translation_cache_engine_hash"),
    )